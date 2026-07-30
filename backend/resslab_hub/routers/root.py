"""
Handle / requests
"""

from os import path
from secrets import compare_digest
from tempfile import TemporaryDirectory

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from resslab_hub import __name__ as name
from resslab_hub import __version__
from resslab_hub.config import settings
from resslab_hub.data.uploader import Type, upload_all
from resslab_hub.data.validator import validate_all
from resslab_hub.models import Info
from resslab_hub.models.validation import (
    FileValidationResult,
    LegacyFileResult,
    ValidationIssue,
    ValidationResponse,
)
from resslab_hub.utils.caching import bump_data_version
from resslab_hub.utils.rate_limit import limiter
from resslab_hub.utils.safe_archive import (
    ArchiveError,
    ArchiveTooLarge,
    safe_extract_targz,
)

router = APIRouter()

security = HTTPBasic()

# Reject obviously oversized uploads before we read the body. The archive
# extraction caps (safe_archive.py) remain the authoritative guard against a
# lying Content-Length; this just fails fast on the honest ones.
MAX_REQUEST_BYTES = 25 * 2**20  # 25 MB


def enforce_request_size(request: Request) -> None:
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > MAX_REQUEST_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Upload exceeds the maximum allowed size.",
                )
        except ValueError:
            pass


def get_current_username(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """
    https://fastapi.tiangolo.com/advanced/security/http-basic-auth/
    """
    current_username = credentials.username
    correct_username: str = settings.api_username  # type: ignore
    is_correct_username = compare_digest(current_username, correct_username)
    current_password = credentials.password
    correct_password: str = settings.get("api_password") or ""
    # Fail closed: when no API password is configured, deny every write request
    # instead of authenticating against an empty/placeholder credential (an empty
    # correct_password would otherwise match an empty supplied password).
    if not correct_password:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Upload API is not configured",
        )
    is_correct_password = compare_digest(current_password, correct_password)
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    return credentials.username


@router.get("/", response_model=Info)
async def root() -> Info:
    """
    Get Info
    """
    return Info(name=name, version=__version__)


@router.get("/healthz")
async def healthz():
    return {"status": "ok"}


@router.post("/upload", dependencies=[Depends(get_current_username)])
async def create_upload_file(
    file: UploadFile = File(...),
    type: Type = Query(...),
    _: None = Depends(enforce_request_size),
):
    try:
        with TemporaryDirectory() as tmpdir:
            safe_extract_targz(file.file, tmpdir)
            [primary_uploads, secondary_uploads] = upload_all(type, [tmpdir])
            # New data is live: expire every browser-cached data response.
            bump_data_version()
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message": "Upload successful",
                    "primary_uploads": primary_uploads,
                    "secondary_uploads": secondary_uploads,
                },
            )
    except ArchiveTooLarge as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)
        )
    except ArchiveError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )
    finally:
        await file.close()


def _issue(err) -> ValidationIssue:
    return ValidationIssue(
        row=err.row,
        column=err.column,
        value=None if err.value is None else str(err.value),
        message=err.message,
    )


def _build_response(results, tmpdir: str) -> ValidationResponse:
    """Assemble the structured (+ legacy) validation response from results."""
    structured = []
    legacy_errors = []
    legacy_valids = []

    for result in results:
        rel_path = path.relpath(result.file_path, tmpdir)
        structured.append(
            FileValidationResult(
                file=result.filename,
                path=rel_path,
                valid=result.is_valid(),
                errors=[_issue(err) for err in result.errors],
                warnings=[_issue(warn) for warn in result.warnings],
            )
        )
        # Legacy string arrays, kept for the data-repo validation CI.
        if result.is_valid():
            legacy_valids.append(
                LegacyFileResult(
                    file=result.filename,
                    valid=True,
                    warnings=[str(warn) for warn in result.warnings],
                )
            )
        else:
            legacy_errors.append(
                LegacyFileResult(
                    file=result.filename,
                    valid=False,
                    errors_count=len(result.errors),
                    errors=[str(err) for err in result.errors],
                    warnings=[str(warn) for warn in result.warnings],
                )
            )

    valid = all(result.is_valid() for result in results)
    return ValidationResponse(
        valid=valid,
        message="Validation successful" if valid else "Validation failed",
        error_count=sum(len(result.errors) for result in results),
        results=structured,
        error_results=legacy_errors,
        valid_results=legacy_valids,
    )


# NOTE(auth): /validate is intentionally unauthenticated. It is a read-only
# check that persists nothing (the archive is parsed as text and discarded), so
# it can stay open for external contributors iterating on their data until
# per-user academic-email auth lands. It is hardened instead: the archive is
# extracted through safe_extract_targz (path-traversal + decompression-bomb
# caps), the request body is size-capped, and the endpoint is rate limited.
# /upload, which writes to the database, stays password-protected above.
@router.post("/validate", response_model=ValidationResponse)
@limiter.limit("30/minute")
async def validate_data(
    request: Request,
    file: UploadFile = File(...),
    type: Type = Query(...),
    _: None = Depends(enforce_request_size),
):
    try:
        with TemporaryDirectory() as tmpdir:
            safe_extract_targz(file.file, tmpdir)

            # cpu=1 forces inline validation in the request path. A large
            # contribution can exceed validate_all's parallel threshold, and the
            # spawn pool re-imports the whole app per worker -- which OOM-kills a
            # memory-capped pod. See _PARALLEL_MIN_TASKS in validator.py.
            results = validate_all(type, [tmpdir], cpu=1)

            # A validation report is a successful operation even when the data
            # has errors: 200 with valid=false. 4xx is reserved for transport
            # problems (400 malformed, 413 too large, 429 rate limited).
            return _build_response(results, tmpdir)
    except ArchiveTooLarge as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)
        )
    except ArchiveError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )
    finally:
        await file.close()


@router.get("/user")
async def get_user(username: str = Depends(get_current_username)):
    return {"username": username}
