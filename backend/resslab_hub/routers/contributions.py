"""
Handle /contributions requests: submit a validated batch as a data-repo PR,
or push a new commit on an open one.
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
from githubkit.exception import RequestFailed

from resslab_hub.auth import roles
from resslab_hub.auth.deps import require_contributions_enabled, require_role
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
from resslab_hub.models.database.auth import User
from resslab_hub.models.validation import ValidationResponse
from resslab_hub.routers.curation import invalidate_pull
from resslab_hub.routers.root import _build_response, enforce_request_size
from resslab_hub.utils.rate_limit import limiter
from resslab_hub.utils.safe_archive import (
    ArchiveError,
    ArchiveTooLarge,
    safe_extract_targz,
)

# Router-level, so it runs before the sign-in check of each route.
router = APIRouter(dependencies=[Depends(require_contributions_enabled)])


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


def _contributor(user: User) -> Contributor:
    """Who the commit is authored by: the signed-in account (#247).

    The commit author and its ``Submitted-by`` trailer both need a real name
    and a proven address. A GitHub-only account may have neither (rare: GitHub
    shares the verified primary address), and cannot add one until the
    profile page lands, so the message says what to do instead.
    """
    if not user.display_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account has no name yet, so it cannot submit.",
        )
    if not user.email or user.email_verified_at is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "This account has no confirmed email address, so it cannot "
                "submit. Sign in with your email address instead."
            ),
        )
    return Contributor(
        name=user.display_name.strip(),
        email=user.email,
        institution=user.institution.strip(),
        orcid=user.orcid.strip(),
        github_login=user.github_login,
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
    except (HTTPException, RequestFailed):
        # A GitHub refusal goes to the handler in main.py, with GitHub's reason.
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )
    finally:
        await file.close()


# Contributor role, not just a session (#248). Being signed in is not by
# itself permission to submit: any address that can receive a code would
# otherwise open pull requests on the data repository. The role comes from an
# academic address or an admin, see `auth/roles.py`. Who submitted is not a form field
# either: it is the account, which is what makes the pull request attributable
# and lets a curator reach the person who opened it.
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
    dismissed_warnings: str = Form("[]"),
    user: User = Depends(require_role(roles.CONTRIBUTOR)),
    _: None = Depends(enforce_request_size),
):
    """
    Re-validate a contribution archive and open a pull request on the data
    repository. Errors block; warnings pass and are listed in the PR body.
    """
    dismissed = _parse_dismissed(dismissed_warnings)
    contributor = _contributor(user)
    return await _run_on_archive(
        file,
        lambda tmpdir: submit_contribution(tmpdir, type, contributor, dismissed),
    )


# Same account as the submission, checked in `update_contribution` against the
# commit trailers on the branch. Or a curator, who can fix anyone's (#248).
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
    dismissed_warnings: str = Form("[]"),
    user: User = Depends(require_role(roles.CONTRIBUTOR)),
    _: None = Depends(enforce_request_size),
):
    """
    Replace an open submission's batch with a new commit on its own branch.
    The pull request updates and its checks rerun; no second review is opened.

    Answers 403 when the submission was made from another account (unless
    the caller is a curator), and 409 when the branch moved since the editor
    loaded it: reload and make the changes again.
    """
    dismissed = _parse_dismissed(dismissed_warnings)
    contributor = _contributor(user)
    response = await _run_on_archive(
        file,
        lambda tmpdir: update_contribution(
            tmpdir,
            pr_number,
            head_sha,
            contributor,
            dismissed,
            as_curator=roles.at_least(user.role, roles.CURATOR),
        ),
    )
    if isinstance(response, ContributionResponse):
        # The queue and the pull request itself are cached by number, not by
        # head sha: without this the update stays invisible for a minute.
        invalidate_pull(pr_number)
    return response
