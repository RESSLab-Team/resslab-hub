"""
Handle / requests
"""

from logging import warning
from os import path
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

from resslab_hub import __name__ as name
from resslab_hub import __version__
from resslab_hub.auth.deps import require_service, require_user_or_service
from resslab_hub.contributions.github import configured
from resslab_hub.contributions.submission import flag_repo_duplicates
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

# Reject obviously oversized uploads before we read the body. The archive
# extraction caps (safe_archive.py) remain the authoritative guard against a
# lying Content-Length; this just fails fast on the honest ones.
# A 200-specimen batch with three curve files each gzips to roughly 10 MB;
# the archive's own uncompressed caps (safe_archive) bound what it expands to.
MAX_REQUEST_BYTES = 50 * 2**20  # 50 MB


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


@router.get("/", response_model=Info)
async def root() -> Info:
    """
    Get Info
    """
    return Info(name=name, version=__version__)


@router.get("/healthz")
async def healthz():
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(request: Request):
    """
    Readiness: 503 until the startup cache warmup (utils/warmup.py) has
    rendered the hot URL space, so deploys don't expose a cold pod.
    """
    if getattr(request.app.state, "warmed", True):
        return {"status": "ready"}
    return JSONResponse(status_code=503, content={"status": "warming"})


@router.post("/upload", dependencies=[Depends(require_service)])
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


# Two kinds of caller, so two ways in (#247): a contributor signed in to the
# editor, or the data repository's CI with the shared machine credential (see
# data-validation.yml, and `make validate-%`). Any signed-in account passes,
# whatever its role: checking a batch writes nothing, and someone who cannot
# submit yet still needs to know their data is clean.
@router.post(
    "/validate",
    response_model=ValidationResponse,
    dependencies=[Depends(require_user_or_service)],
)
@limiter.limit("30/minute")
async def validate_data(
    request: Request,
    file: UploadFile = File(...),
    type: Type = Query(...),
    # Opt-in: the contribution editor flags ids that already exist in the
    # database as errors. The data-repo CI validates the full repo CSVs, whose
    # ids are all ingested already, so it must keep the default.
    check_duplicates: bool = Query(False),
    _: None = Depends(enforce_request_size),
):
    try:
        with TemporaryDirectory() as tmpdir:
            safe_extract_targz(file.file, tmpdir)

            # cpu=1 forces inline validation in the request path. A large
            # contribution can exceed validate_all's parallel threshold, and the
            # spawn pool re-imports the whole app per worker -- which OOM-kills a
            # memory-capped pod. See _PARALLEL_MIN_TASKS in validator.py.
            results = validate_all(
                type, [tmpdir], cpu=1, check_duplicate_ids=check_duplicates
            )
            # Same repo-level duplicate check the submission enforces, so a
            # contributor learns about a clash while editing, not on submit.
            # Best effort: GitHub being unreachable must not fail the check.
            if check_duplicates and configured():
                try:
                    await flag_repo_duplicates(tmpdir, type, results)
                except Exception as exc:  # noqa: BLE001
                    warning(f"Data-repo duplicate check skipped: {exc}")

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


# The machine credential's own probe: the data repository's workflows call this
# with `curl -f -u user:$API_PASSWORD` before uploading or validating, to fail
# early on a bad password. People use GET /auth/me instead.
@router.get("/user")
async def get_user(username: str = Depends(require_service)):
    return {"username": username}
