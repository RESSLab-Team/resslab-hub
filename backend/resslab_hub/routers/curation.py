"""
Read-only curation endpoints: project open contribution PRs for the review UI.

Nothing about a submission is stored in the app database — the PR on the data
repository is the source of truth (epic #255). These endpoints reconstruct a
submitted batch from the PR itself: the appended rows are the head-CSV rows
whose id is absent from the base CSV, the contributor comes from the PR body,
and quality flags come from re-running the same server-side validation the
submission went through.

Who sees what (#248). The queue is the lab's work list: curators only, the
role that write access on the data repository gives. One submission can be
read by a curator, or by the person who made it, since the edit step (#321)
loads it back through these same endpoints. Nothing here reveals more than the
public data-repo pull request already does. Approving and merging stay on
GitHub. The per-IP rate limits and the TTL caches keyed by the PR head sha
also protect the GitHub App's API budget.
"""

import asyncio
import os
import re
from os import path
from tempfile import TemporaryDirectory
from time import monotonic
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse

from resslab_hub.auth import roles
from resslab_hub.auth.deps import (
    require_contributions_enabled,
    require_role,
    require_user,
)
from resslab_hub.contributions.github import (
    MAX_PARALLEL_CALLS,
    DataRepoClient,
    configured,
)
from resslab_hub.contributions.projection import (
    SubmissionError,
    _layout_for,
    classify_files,
    split_batch,
    type_for_branch,
)
from resslab_hub.contributions.submission import (
    _read_csv,
    _write_csv,
    read_provenance,
)
from resslab_hub.contributions.trailers import Provenance, owns_submission
from resslab_hub.data.uploader import Type
from resslab_hub.data.validator import validate_all
from resslab_hub.models.curation import (
    CurationComment,
    CurationCommentsResponse,
    CurationContributor,
    CurationDetail,
    CurationExperiment,
    CurationListResponse,
    CurationSummary,
)
from resslab_hub.models.validation import (
    FileValidationResult,
    ValidationIssue,
    ValidationResponse,
)
from resslab_hub.routers.root import _build_response
from resslab_hub.utils.rate_limit import limiter

# Router-level, so it runs before the sign-in check of each route.
router = APIRouter(dependencies=[Depends(require_contributions_enabled)])

#: Caps for the validation endpoint's file downloads. A submission beyond them
#: still validates its primary CSV; skipped curves get an explicit warning.
MAX_CURVE_FILE_BYTES = 5 * 2**20
MAX_CURVE_TOTAL_BYTES = 20 * 2**20
MAX_CURVE_FILES = 100

LIST_TTL_SECONDS = 60
DETAIL_TTL_SECONDS = 600
#: Comments are the one part of a PR that moves without the head sha moving,
#: so their cache is keyed on the number alone and expires quickly.
COMMENTS_TTL_SECONDS = 30


class _TTLCache:
    """Minimal in-process TTL cache; per replica, like the rate limiter."""

    def __init__(self, max_entries: int = 256):
        self._entries: dict = {}
        self._max = max_entries

    def get(self, key):
        entry = self._entries.get(key)
        if entry is None:
            return None
        expiry, value = entry
        if monotonic() > expiry:
            del self._entries[key]
            return None
        return value

    def drop(self, key) -> None:
        self._entries.pop(key, None)

    def put(self, key, value, ttl: float):
        if len(self._entries) >= self._max:
            now = monotonic()
            self._entries = {k: v for k, v in self._entries.items() if v[0] > now}
            while len(self._entries) >= self._max:
                self._entries.pop(next(iter(self._entries)))
        self._entries[key] = (monotonic() + ttl, value)


_cache = _TTLCache()


def invalidate_pull(pr_number: int) -> None:
    """Forget what we know about one pull request.

    The detail, validation and file caches are keyed by head sha, so a new
    commit expires them on its own. The pull request itself and the queue
    listing are not, so an update made through the Hub would stay invisible
    for a minute and the next update would collide on a stale head sha.
    """
    _cache.drop(("pull", pr_number))
    _cache.drop("list")


async def open_pulls(client: DataRepoClient) -> List[dict]:
    """The open pull requests into the base branch, cached for a minute.

    One GitHub call for the queue and the verification tab (#253) together.
    """
    cached = _cache.get("list")
    if cached is None:
        cached = await client.list_open_pulls()
        _cache.put("list", cached, LIST_TTL_SECONDS)
    return cached


def invalidate_open_pulls() -> None:
    """Forget the list, so a pull request the Hub just opened shows at once."""
    _cache.drop("list")


def _parse_pr_body(body: str) -> Tuple[Optional[int], Optional[CurationContributor]]:
    """Best-effort parse of build_pr_body's deterministic format."""
    count = None
    match = re.search(r"\*\*Experiments\*\*: (\d+)", body)
    if match:
        count = int(match.group(1))
    contributor = None
    match = re.search(r"\*\*Contributor\*\*: (.*?) \([^)]*\)(?:, (.*))?$", body, re.M)
    if match:
        contributor = CurationContributor(
            name=match.group(1).strip(), institution=(match.group(2) or "").strip()
        )
        orcid = re.search(r"\*\*ORCID\*\*: (.*)$", body, re.M)
        if orcid:
            contributor.orcid = orcid.group(1).strip()
        github = re.search(r"\*\*GitHub\*\*: @(\S+)$", body, re.M)
        if github:
            contributor.github_login = github.group(1).strip()
    return count, contributor


def _summary(pull: dict, input_type: Type) -> CurationSummary:
    count, contributor = _parse_pr_body(pull["body"])
    return CurationSummary(
        pr_number=pull["number"],
        pr_url=pull["html_url"],
        title=pull["title"],
        branch=pull["head_ref"],
        type=input_type.value,
        draft=pull["draft"],
        created_at=pull["created_at"],
        updated_at=pull["updated_at"],
        experiment_count=count,
        contributor=contributor,
    )


async def _fetch_pull(client: DataRepoClient, pr_number: int) -> Tuple[dict, Type]:
    """The PR, guaranteed open and contribution-shaped, else 404."""
    cached = _cache.get(("pull", pr_number))
    if cached is None:
        try:
            cached = await client.get_pull(pr_number)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="This pull request does not exist on the data repository.",
            )
        _cache.put(("pull", pr_number), cached, LIST_TTL_SECONDS)
    input_type = type_for_branch(cached["head_ref"])
    if cached["state"] != "open" or input_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This pull request is not an open contribution.",
        )
    return cached, input_type


async def _build_detail(
    client: DataRepoClient, pull: dict, input_type: Type
) -> CurationDetail:
    head_sha = pull["head_sha"]
    cached = _cache.get(("detail", pull["number"], head_sha))
    if cached is not None:
        return cached

    layout = _layout_for(input_type)
    files = classify_files(await client.list_pull_files(pull["number"]), input_type)
    detail = CurationDetail(
        **_summary(pull, input_type).model_dump(),
        state=pull["state"],
        head_sha=head_sha,
        body=pull["body"],
        submitted_at="",
        dismissed_warnings=[],
        columns=[],
        experiments=[],
        files=files,
        reconstruction_warning=None,
    )

    # Provenance is informative, never load-bearing: any failure downgrades to
    # a reconstruction warning instead of breaking the review screen.
    provenance = await read_provenance(client, pull["number"], head_sha, files)
    if provenance is None:
        detail.reconstruction_warning = (
            "The submission's commit trailers could not be read; contributor "
            "details come from the pull request body."
        )
    else:
        # Who may edit it, kept beside the detail rather than in it: the
        # detail is cached across users, the answer is per user.
        _cache.put(("owner", pull["number"], head_sha), provenance, DETAIL_TTL_SECONDS)
        detail.contributor = CurationContributor(
            name=provenance.name,
            institution=provenance.institution,
            orcid=provenance.orcid,
            github_login=provenance.github_login,
        )
        detail.submitted_at = provenance.submitted_at
        detail.dismissed_warnings = list(provenance.dismissed_warnings)

    # The appended batch = head rows whose id is not in the base CSV. Robust to
    # CRLF, column order and legacy columns because rows are keyed by name.
    head_text = await client.get_file_text(layout.primary_csv, ref=head_sha)
    base_text = await client.get_file_text(layout.primary_csv)
    head_header, head_rows = _read_csv(head_text)
    base_header, base_rows = _read_csv(base_text)
    try:
        head_id = head_header.index("id")
        base_id = base_header.index("id")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The data repository's primary CSV has no 'id' column.",
        )
    existing = {row[base_id].strip() for row in base_rows if base_id < len(row)}
    detail.columns = head_header
    _, batch_rows = split_batch(head_header, head_rows, existing)
    for row in batch_rows:
        cells = {
            name: (row[position] if position < len(row) else "")
            for position, name in enumerate(head_header)
        }
        detail.experiments.append(
            CurationExperiment(id=row[head_id].strip(), cells=cells)
        )

    if (
        detail.experiment_count is not None
        and detail.experiment_count != len(detail.experiments)
        and detail.reconstruction_warning is None
    ):
        detail.reconstruction_warning = (
            "The reconstructed batch does not match the pull request's "
            "experiment count — the base branch may have moved. Review the "
            "diff on GitHub."
        )

    _cache.put(("detail", pull["number"], head_sha), detail, DETAIL_TTL_SECONDS)
    return detail


async def _build_validation(
    client: DataRepoClient, detail: CurationDetail, input_type: Type
) -> ValidationResponse:
    """Re-validate the reconstructed batch in a repo-shaped temp directory."""
    layout = _layout_for(input_type)
    skipped: List[str] = []
    with TemporaryDirectory() as tmpdir:
        primary = path.join(tmpdir, layout.primary_csv)
        # The same iteration order as detail.experiments, so ValidationIssue
        # rows line up with the displayed batch (pinned by a backend test).
        rows = [
            [experiment.cells.get(name, "") for name in detail.columns]
            for experiment in detail.experiments
        ]
        os.makedirs(path.dirname(primary) or tmpdir, exist_ok=True)
        with open(primary, "w", encoding="utf-8") as file:
            file.write(_write_csv(detail.columns, rows))

        total = 0
        curve_files = [f for f in detail.files if f.kind == "timeseries"]
        wanted = curve_files[:MAX_CURVE_FILES]

        limit = asyncio.Semaphore(MAX_PARALLEL_CALLS)

        async def read(curve) -> Optional[str]:
            async with limit:
                try:
                    return await client.get_file_text(curve.path, ref=detail.head_sha)
                except Exception:
                    return None

        # Downloaded together, then applied in the original order so the size
        # budget and `skipped` stay deterministic.
        texts = await asyncio.gather(*(read(curve) for curve in wanted))
        for curve, text in zip(wanted, texts):
            if text is None:
                skipped.append(curve.path)
                continue
            size = len(text.encode("utf-8"))
            if size > MAX_CURVE_FILE_BYTES or total + size > MAX_CURVE_TOTAL_BYTES:
                skipped.append(curve.path)
                continue
            total += size
            target = path.join(tmpdir, curve.path)
            os.makedirs(path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8") as file:
                file.write(text)
        skipped.extend(curve.path for curve in curve_files[MAX_CURVE_FILES:])

        try:
            results = validate_all(
                input_type, [tmpdir], cpu=1, check_duplicate_ids=True
            )
        except NotImplementedError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Server-side validation is not available for this database.",
            )
        response = _build_response(results, tmpdir)

    for rel in skipped:
        response.results.append(
            FileValidationResult(
                file=path.basename(rel),
                path=rel,
                valid=True,
                warnings=[
                    ValidationIssue(
                        row=0,
                        column="file",
                        message=(
                            "This file was too large to re-check here — "
                            "review it on GitHub."
                        ),
                    )
                ],
            )
        )
    return response


async def _owner(
    client: DataRepoClient, pull: dict, input_type: Type
) -> Optional[Provenance]:
    """Who made the submission. ``_build_detail`` caches it beside the detail."""
    key = ("owner", pull["number"], pull["head_sha"])
    provenance = _cache.get(key)
    if provenance is None:
        detail = await _build_detail(client, pull, input_type)
        # The detail can outlive its owner entry in the cache.
        provenance = _cache.get(key) or await read_provenance(
            client, pull["number"], pull["head_sha"], detail.files
        )
        if provenance is not None:
            _cache.put(key, provenance, DETAIL_TTL_SECONDS)
    return provenance


async def _check_access(
    request: Request, client: DataRepoClient, pull: dict, input_type: Type
) -> None:
    """A curator reads any submission, anyone else only their own (#248)."""
    user = getattr(request.state, "user", None)
    if user is not None and roles.at_least(user.role, roles.CURATOR):
        return
    if user is not None and owns_submission(
        await _owner(client, pull, input_type), user.email or ""
    ):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only curators and the person who made this submission can see it.",
    )


# The gates go on the decorator, not in the signature: the curation tests call
# these functions directly, where FastAPI dependencies never run. The per-PR
# check needs the pull request, so it runs in the handler (`_check_access`).
@router.get(
    "/contributions",
    response_model=CurationListResponse,
    dependencies=[Depends(require_role(roles.CURATOR))],
)
@limiter.limit("30/minute")
async def list_contributions(request: Request) -> CurationListResponse:
    """
    Open contribution pull requests on the data repository, for the review
    queue. Returns ``configured: false`` (not an error) on deployments without
    the GitHub App.
    """
    if not configured():
        return CurationListResponse(configured=False)
    items = []
    for pull in await open_pulls(DataRepoClient()):
        input_type = type_for_branch(pull["head_ref"])
        if input_type is not None:
            items.append(_summary(pull, input_type))
    return CurationListResponse(configured=True, items=items)


@router.get(
    "/contributions/{pr_number}",
    response_model=CurationDetail,
    dependencies=[Depends(require_user)],
)
@limiter.limit("30/minute")
async def get_contribution(request: Request, pr_number: int) -> CurationDetail:
    """
    Everything the review screen needs about one submission, reconstructed
    from the pull request at its current head commit.
    """
    if not configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Curation is not enabled on this deployment.",
        )
    client = DataRepoClient()
    pull, input_type = await _fetch_pull(client, pr_number)
    try:
        await _check_access(request, client, pull, input_type)
        detail = await _build_detail(client, pull, input_type)
    except (HTTPException, SubmissionError):
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"The submission could not be read from the data repository: {exc}",
        )
    return detail.model_copy(update={"mine": _is_mine(request, pr_number, detail)})


def _is_mine(request: Request, pr_number: int, detail: CurationDetail) -> bool:
    """Whether the signed-in account made this submission (#247)."""
    user = getattr(request.state, "user", None)
    if user is None:
        return False
    provenance = _cache.get(("owner", pr_number, detail.head_sha))
    return owns_submission(provenance, user.email or "")


@router.get(
    "/contributions/{pr_number}/validation",
    response_model=ValidationResponse,
    dependencies=[Depends(require_user)],
)
@limiter.limit("10/minute")
async def get_contribution_validation(
    request: Request, pr_number: int
) -> ValidationResponse:
    """
    Re-run server-side validation on the reconstructed batch, producing the
    same response shape as ``/validate``. Issue rows index into the detail
    endpoint's ``experiments`` list (row N = experiments[N-1]).
    """
    if not configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Curation is not enabled on this deployment.",
        )
    client = DataRepoClient()
    pull, input_type = await _fetch_pull(client, pr_number)
    await _check_access(request, client, pull, input_type)
    head_sha = pull["head_sha"]
    cached = _cache.get(("validation", pr_number, head_sha))
    if cached is not None:
        return cached
    detail = await _build_detail(client, pull, input_type)
    response = await _build_validation(client, detail, input_type)
    _cache.put(("validation", pr_number, head_sha), response, DETAIL_TTL_SECONDS)
    return response


@router.get(
    "/contributions/{pr_number}/comments",
    response_model=CurationCommentsResponse,
    dependencies=[Depends(require_user)],
)
@limiter.limit("30/minute")
async def get_contribution_comments(
    request: Request, pr_number: int
) -> CurationCommentsResponse:
    """
    The submission's discussion, oldest first, with the pull request body as
    the opening entry (it is the submission summary the contributor wrote).

    Read-only: replying, requesting changes and approving still happen on
    GitHub (#254).
    """
    if not configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Curation is not enabled on this deployment.",
        )
    client = DataRepoClient()
    pull, input_type = await _fetch_pull(client, pr_number)
    await _check_access(request, client, pull, input_type)
    cached = _cache.get(("comments", pr_number))
    if cached is not None:
        return cached
    try:
        comments = await client.list_issue_comments(pr_number)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"The discussion could not be read from the data repository: {exc}",
        )
    items = [
        CurationComment(
            id=0,
            author=pull.get("author", ""),
            author_type=pull.get("author_type", ""),
            body=pull.get("body", ""),
            html_url=pull["html_url"],
            created_at=pull["created_at"],
            updated_at=pull["created_at"],
            is_body=True,
        )
    ]
    items.extend(
        CurationComment(
            id=comment["id"],
            author=comment["author"],
            author_type=comment["author_type"],
            body=comment["body"],
            html_url=comment["html_url"],
            created_at=comment["created_at"],
            updated_at=comment["updated_at"],
            is_body=False,
        )
        for comment in comments
    )
    response = CurationCommentsResponse(pr_number=pr_number, items=items)
    _cache.put(("comments", pr_number), response, COMMENTS_TTL_SECONDS)
    return response


@router.get(
    "/contributions/{pr_number}/files",
    response_class=PlainTextResponse,
    dependencies=[Depends(require_user)],
)
# The edit step (#321) loads one file per request to fill the editor, so a
# batch with many curves needs more headroom than a curator reading one.
@limiter.limit("120/minute")
async def get_contribution_file(
    request: Request, pr_number: int, path_param: str = Query(..., alias="path")
) -> str:
    """
    Raw text of one file added by the submission (time-series preview).
    Only paths the PR actually adds inside the type's layout are served.
    """
    if not configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Curation is not enabled on this deployment.",
        )
    client = DataRepoClient()
    pull, input_type = await _fetch_pull(client, pr_number)
    await _check_access(request, client, pull, input_type)
    head_sha = pull["head_sha"]
    cached = _cache.get(("file", head_sha, path_param))
    if cached is not None:
        return cached
    detail = await _build_detail(client, pull, input_type)
    allowed = {
        file.path for file in detail.files if file.kind in ("timeseries", "primary")
    }
    if path_param not in allowed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This file is not part of the submission.",
        )
    try:
        text = await client.get_file_text(path_param, ref=head_sha)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The file could not be read from the data repository.",
        )
    _cache.put(("file", head_sha, path_param), text, DETAIL_TTL_SECONDS)
    return text
