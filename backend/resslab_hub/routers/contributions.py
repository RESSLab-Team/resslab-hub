"""
Handle /contributions requests: submit a validated batch as a data-repo PR.
"""

import json
from tempfile import TemporaryDirectory

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse

from resslab_hub.contributions.github import configured
from resslab_hub.contributions.submission import (
    Contributor,
    SubmissionError,
    SubmissionValidationFailed,
    submit_contribution,
)
from resslab_hub.data.uploader import Type
from resslab_hub.models.contribution import ContributionResponse
from resslab_hub.models.validation import ValidationResponse
from resslab_hub.routers.root import (
    _build_response,
    enforce_request_size,
    get_current_username,
)
from resslab_hub.utils.rate_limit import limiter
from resslab_hub.utils.safe_archive import (
    ArchiveError,
    ArchiveTooLarge,
    safe_extract_targz,
)

router = APIRouter()


def _parse_dismissed(raw: str) -> list:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="dismissed_warnings must be a JSON array of strings.",
        )
    if not isinstance(parsed, list) or not all(
        isinstance(entry, str) for entry in parsed
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="dismissed_warnings must be a JSON array of strings.",
        )
    return parsed


# NOTE(auth): unlike /validate, submitting has side effects (a PR on the data
# repo), so it keeps the shared HTTP Basic gate until per-user academic auth
# (#247) lands. The strict rate limit bounds PR spam from a leaked credential.
@router.post(
    "/contributions",
    response_model=ContributionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={422: {"model": ValidationResponse}},
    dependencies=[Depends(get_current_username)],
)
@limiter.limit("5/hour")
async def create_contribution(
    request: Request,
    file: UploadFile = File(...),
    type: Type = Query(...),
    contributor_name: str = Form(..., min_length=1, max_length=200),
    contributor_email: str = Form(..., min_length=3, max_length=200),
    institution: str = Form("", max_length=200),
    orcid: str = Form("", max_length=50),
    dismissed_warnings: str = Form("[]"),
    _: None = Depends(enforce_request_size),
):
    """
    Re-validate a contribution archive and open a pull request on the data
    repository. Errors block; warnings pass and are listed in the PR body.
    """
    if not configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Submissions are not enabled on this deployment.",
        )
    dismissed = _parse_dismissed(dismissed_warnings)
    contributor = Contributor(
        name=contributor_name.strip(),
        email=contributor_email.strip(),
        institution=institution.strip(),
        orcid=orcid.strip(),
    )
    try:
        with TemporaryDirectory() as tmpdir:
            safe_extract_targz(file.file, tmpdir)
            result = await submit_contribution(tmpdir, type, contributor, dismissed)
            return ContributionResponse(
                pr_url=result.pr_url,
                pr_number=result.pr_number,
                branch=result.branch,
            )
    except SubmissionValidationFailed as exc:
        response = _build_response(exc.results, tmpdir)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=response.model_dump(),
        )
    except SubmissionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    except ArchiveTooLarge as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)
        )
    except ArchiveError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )
    finally:
        await file.close()
