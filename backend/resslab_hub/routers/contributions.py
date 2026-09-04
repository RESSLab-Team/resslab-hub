"""
Handle /contributions requests: submit a validated batch as a data-repo PR.
"""

import json
from tempfile import TemporaryDirectory
from typing import Union

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
    SubmissionResult,
    SubmissionValidationFailed,
    submit_contribution,
    update_contribution,
)
from resslab_hub.data.uploader import Type
from resslab_hub.models.contribution import ContributionResponse
from resslab_hub.models.validation import ValidationResponse
from resslab_hub.routers.curation import invalidate_pull
from resslab_hub.routers.root import _build_response, enforce_request_size
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


def _contributor(name: str, email: str, institution: str, orcid: str) -> Contributor:
    """Who the commit is authored by: self-declared until #247 lands."""
    return Contributor(
        name=name.strip(),
        email=email.strip(),
        institution=institution.strip(),
        orcid=orcid.strip(),
    )


async def _run_on_archive(
    file: UploadFile, run
) -> Union[ContributionResponse, JSONResponse]:
    """Extract the upload, hand the directory to `run`, map failures to HTTP.

    Shared by the submit and the update endpoints: both take the same archive
    and answer the same way, a failed re-validation included (422 with the
    full report, so the editor can put the errors back on the cells).
    """
    if not configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Submissions are not enabled on this deployment.",
        )
    try:
        with TemporaryDirectory() as tmpdir:
            safe_extract_targz(file.file, tmpdir)
            try:
                result: SubmissionResult = await run(tmpdir)
            except SubmissionValidationFailed as exc:
                return JSONResponse(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    content=_build_response(exc.results, tmpdir).model_dump(),
                )
            return ContributionResponse(
                pr_url=result.pr_url,
                pr_number=result.pr_number,
                branch=result.branch,
                head_sha=result.head_sha,
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


# NOTE(auth): open, like /validate. The shared HTTP Basic credential also
# guards /upload, and a browser-side gate would have to ship it in the JS
# bundle — publishing the ingestion password to every visitor. Until per-user
# academic auth (#247) lands, the defences are the rate limit below, mandatory
# server-side validation, and the fact that a submission only ever becomes a
# pull request a curator has to review.
@router.post(
    "/contributions",
    response_model=ContributionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={422: {"model": ValidationResponse}},
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
    dismissed = _parse_dismissed(dismissed_warnings)
    contributor = _contributor(contributor_name, contributor_email, institution, orcid)
    return await _run_on_archive(
        file,
        lambda tmpdir: submit_contribution(tmpdir, type, contributor, dismissed),
    )


# NOTE(auth): open like the POST above; what the caller proves and what still
# protects the branch is in `update_contribution`.
@router.put(
    "/contributions/{pr_number}",
    response_model=ContributionResponse,
    responses={422: {"model": ValidationResponse}},
)
@limiter.limit("10/hour")
async def update_open_contribution(
    request: Request,
    pr_number: int,
    file: UploadFile = File(...),
    head_sha: str = Form(..., min_length=40, max_length=40),
    contributor_name: str = Form(..., min_length=1, max_length=200),
    contributor_email: str = Form(..., min_length=3, max_length=200),
    institution: str = Form("", max_length=200),
    orcid: str = Form("", max_length=50),
    dismissed_warnings: str = Form("[]"),
    _: None = Depends(enforce_request_size),
):
    """
    Replace an open submission's batch with a new commit on its own branch.
    The pull request updates and its checks rerun; no second review is opened.

    Answers 409 when the branch moved since the editor loaded it: reload and
    make the changes again.
    """
    dismissed = _parse_dismissed(dismissed_warnings)
    contributor = _contributor(contributor_name, contributor_email, institution, orcid)
    response = await _run_on_archive(
        file,
        lambda tmpdir: update_contribution(
            tmpdir, pr_number, head_sha, contributor, dismissed
        ),
    )
    if isinstance(response, ContributionResponse):
        # The queue and the pull request itself are cached by number, not by
        # head sha: without this the update stays invisible for a minute.
        invalidate_pull(pr_number)
    return response
