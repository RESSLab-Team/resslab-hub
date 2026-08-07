"""
Read-only curation endpoints: project open contribution PRs for the review UI.

Nothing about a submission is stored in the app database — the PR on the data
repository is the source of truth (epic #255). These endpoints reconstruct a
submitted batch from the PR itself: the appended rows are the head-CSV rows
whose id is absent from the base CSV, the contributor comes from the PR body,
and quality flags come from re-running the same server-side validation the
submission went through.

NOTE(auth): open, like POST /contributions — the review interface ships before
per-user auth (#247) and roles (#248), and approving/merging stays on GitHub,
so these endpoints only ever reveal what the public data-repo PR already shows
(minus the contributor's email). The defences are per-IP rate limits and TTL
caches keyed by the PR head sha, which also protect the GitHub App's API
budget.
"""

import json
import os
import re
from os import path
from tempfile import TemporaryDirectory
from time import monotonic
from typing import List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse

from resslab_hub.contributions.github import DataRepoClient, configured
from resslab_hub.contributions.submission import (
    SAFE_ID_PATTERN,
    SubmissionError,
    _layout_for,
    _read_csv,
    _type_slug,
    _write_csv,
)
from resslab_hub.data.uploader import Type
from resslab_hub.data.validator import validate_all
from resslab_hub.models.curation import (
    CurationContributor,
    CurationDetail,
    CurationExperiment,
    CurationFile,
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

router = APIRouter()

#: Caps for the validation endpoint's file downloads. A submission beyond them
#: still validates its primary CSV; skipped curves get an explicit warning.
MAX_CURVE_FILE_BYTES = 5 * 2**20
MAX_CURVE_TOTAL_BYTES = 20 * 2**20
MAX_CURVE_FILES = 100

LIST_TTL_SECONDS = 60
DETAIL_TTL_SECONDS = 600


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

    def put(self, key, value, ttl: float):
        if len(self._entries) >= self._max:
            now = monotonic()
            self._entries = {k: v for k, v in self._entries.items() if v[0] > now}
            while len(self._entries) >= self._max:
                self._entries.pop(next(iter(self._entries)))
        self._entries[key] = (monotonic() + ttl, value)


_cache = _TTLCache()


def _type_for_branch(branch: str) -> Optional[Type]:
    """``contrib/<type_slug>/<name>`` -> the uploader Type, else None."""
    parts = branch.split("/")
    if len(parts) < 3 or parts[0] != "contrib":
        return None
    try:
        return Type("all-" + parts[1])
    except ValueError:
        return None


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


def _classify_files(files: List[dict], input_type: Type) -> List[CurationFile]:
    """Classify the PR's changed files against the type's known layout."""
    layout = _layout_for(input_type)
    slug = _type_slug(input_type)
    classified = []
    for file in files:
        rel = file["path"]
        directory, filename = path.split(rel)
        stem = path.splitext(filename)[0]
        if rel == layout.primary_csv:
            kind = CurationFile(path=rel, kind="primary")
        elif (
            directory in layout.curve_dirs
            and filename.endswith(".csv")
            and SAFE_ID_PATTERN.fullmatch(stem)
        ):
            kind = CurationFile(
                path=rel,
                kind="timeseries",
                timeseries_dir=directory,
                experiment_id=stem,
            )
        elif directory == f"contributions/{slug}" and filename.endswith(".json"):
            kind = CurationFile(path=rel, kind="provenance")
        else:
            kind = CurationFile(path=rel, kind="other")
        classified.append(kind)
    return classified


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
    input_type = _type_for_branch(cached["head_ref"])
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
    files = _classify_files(await client.list_pull_files(pull["number"]), input_type)
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
    provenance_paths = [f.path for f in files if f.kind == "provenance"]
    if provenance_paths:
        try:
            provenance = json.loads(
                await client.get_file_text(provenance_paths[0], ref=head_sha)
            )
            contributor = provenance.get("contributor", {})
            detail.contributor = CurationContributor(
                name=str(contributor.get("name", "")),
                institution=str(contributor.get("institution", "")),
                orcid=str(contributor.get("orcid", "")),
            )
            detail.submitted_at = str(provenance.get("submitted_at", ""))
            dismissed = provenance.get("dismissed_warnings", [])
            if isinstance(dismissed, list):
                detail.dismissed_warnings = [str(w) for w in dismissed]
        except Exception:
            detail.reconstruction_warning = (
                "The provenance record could not be read; contributor details "
                "come from the pull request body."
            )

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
    for row in head_rows:
        row_id = row[head_id].strip() if head_id < len(row) else ""
        if not row_id or row_id in existing:
            continue
        cells = {
            name: (row[position] if position < len(row) else "")
            for position, name in enumerate(head_header)
        }
        detail.experiments.append(CurationExperiment(id=row_id, cells=cells))

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
        for curve in curve_files[:MAX_CURVE_FILES]:
            try:
                text = await client.get_file_text(curve.path, ref=detail.head_sha)
            except Exception:
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


@router.get("/contributions", response_model=CurationListResponse)
@limiter.limit("30/minute")
async def list_contributions(request: Request) -> CurationListResponse:
    """
    Open contribution pull requests on the data repository, for the review
    queue. Returns ``configured: false`` (not an error) on deployments without
    the GitHub App.
    """
    if not configured():
        return CurationListResponse(configured=False)
    cached = _cache.get("list")
    if cached is None:
        client = DataRepoClient()
        cached = await client.list_open_pulls()
        _cache.put("list", cached, LIST_TTL_SECONDS)
    items = []
    for pull in cached:
        input_type = _type_for_branch(pull["head_ref"])
        if input_type is not None:
            items.append(_summary(pull, input_type))
    return CurationListResponse(configured=True, items=items)


@router.get("/contributions/{pr_number}", response_model=CurationDetail)
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
        return await _build_detail(client, pull, input_type)
    except (HTTPException, SubmissionError):
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"The submission could not be read from the data repository: {exc}",
        )


@router.get("/contributions/{pr_number}/validation", response_model=ValidationResponse)
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
    head_sha = pull["head_sha"]
    cached = _cache.get(("validation", pr_number, head_sha))
    if cached is not None:
        return cached
    detail = await _build_detail(client, pull, input_type)
    response = await _build_validation(client, detail, input_type)
    _cache.put(("validation", pr_number, head_sha), response, DETAIL_TTL_SECONDS)
    return response


@router.get("/contributions/{pr_number}/files", response_class=PlainTextResponse)
@limiter.limit("60/minute")
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
