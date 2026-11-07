"""
Turn a validated contribution archive into a pull request on the data repo.

The archive is the same tar.gz the frontend sends to /validate: the batch's
primary CSV plus time-series files, laid out exactly like the data repository.
The flow re-validates server-side, enforces the path allowlist, appends the
batch rows to the repo's primary CSV at HEAD, and commits everything through
the Git Data API. Who submitted travels in the commit message as trailers, see
``trailers.py``.

Security invariants (epic #255): client-supplied paths are never trusted — the
only writable locations are derived here from the uploader's own type map; ids
must be safe file names (``SAFE_ID_PATTERN``, shared with the validator so the
quality check reports a bad id before submission); CSV cells that could be read as
spreadsheet formulas are prefix-escaped.
"""

import asyncio
import csv
import io
import json
import logging
import re
import secrets
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from fnmatch import fnmatch
from os import path, walk
from time import monotonic
from typing import Dict, Iterable, List, Optional, Set, Tuple

from resslab_hub.config import settings
from resslab_hub.contributions.github import (
    DataRepoClient,
    NewFile,
    describe_error,
)
from resslab_hub.contributions.projection import (
    SubmissionError,
    SubmissionValidationFailed,
    _Layout,
    _layout_for,
    _type_slug,
    classify_files,
    from_fork,
    split_batch,
    type_for_branch,
)
from resslab_hub.contributions.reviewers import request_reviews
from resslab_hub.contributions.trailers import (
    Provenance,
    build_commit_message,
    owns_submission,
    provenance_from_commits,
    provenance_from_record,
)
from resslab_hub.data.common import SAFE_ID_PATTERN, SAFE_ID_RULE
from resslab_hub.data.curation_status import STATUS_COLUMN, UNVERIFIED
from resslab_hub.data.uploader import Type
from resslab_hub.data.validator import ValidationResult, validate_all

logger = logging.getLogger(__name__)

#: Cells starting with these can execute as formulas when the CSV is opened in
#: a spreadsheet. Numbers are exempt: "-1.5" is data, not a formula.
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


@dataclass
class Contributor:
    name: str
    email: str
    institution: str = ""
    orcid: str = ""
    #: GitHub login, when the contributor linked one (#247). Written into the
    #: pull request as an @mention, so they are notified of every review
    #: comment and can answer where the review happens.
    github_login: str = ""


@dataclass
class SubmissionResult:
    pr_url: str
    pr_number: int
    branch: str
    #: Commit the submission now points at. The editor sends it back on the
    #: next update so a branch that moved meanwhile is caught (409).
    head_sha: str = ""


def _archive_files(tmpdir: str) -> List[str]:
    files = []
    for root, _, names in walk(tmpdir):
        for name in names:
            files.append(path.relpath(path.join(root, name), tmpdir))
    return sorted(files)


def check_paths(tmpdir: str, input_type: Type) -> _Layout:
    """Reject any archive entry outside the type's known locations."""
    layout = _layout_for(input_type)
    for rel in _archive_files(tmpdir):
        if rel == layout.primary_csv or rel in layout.dictionary_csvs:
            continue
        directory, filename = path.split(rel)
        stem = path.splitext(filename)[0]
        if (
            directory in layout.curve_dirs
            and fnmatch(filename, "*.csv")
            and SAFE_ID_PATTERN.fullmatch(stem)
        ):
            continue
        raise SubmissionError(400, f"File '{rel}' is not an accepted location.")
    return layout


def escape_formula(cell: str) -> str:
    """Prefix-escape a cell that a spreadsheet would evaluate as a formula."""
    if not cell.startswith(FORMULA_PREFIXES):
        return cell
    try:
        Decimal(cell)
        return cell
    except (InvalidOperation, ValueError):
        return f"'{cell}"


def _read_csv(text: str) -> tuple[List[str], List[List[str]]]:
    # Excel-exported repo CSVs may carry a UTF-8 BOM; never let it glue itself
    # onto the first header name.
    rows = list(csv.reader(io.StringIO(text.lstrip("\ufeff"))))
    if not rows:
        raise SubmissionError(400, "The primary CSV is empty.")
    return rows[0], [row for row in rows[1:] if any(cell.strip() for cell in row)]


def _write_csv(
    header: List[str], rows: List[List[str]], lineterminator: str = "\n"
) -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator=lineterminator)
    writer.writerow(header)
    writer.writerows(rows)
    return out.getvalue()


def normalize_csv_text(text: str) -> str:
    """
    Make a contributor's CSV acceptable to the data repository's line-ending
    check without touching its data: drop a UTF-8 BOM, use LF line endings,
    and end the file with exactly one newline. Spreadsheet exports routinely
    violate all three, and none is worth bouncing a submission for.
    """
    text = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    text = text.rstrip("\n")
    return text + "\n" if text else ""


def batch_ids(header: List[str], rows: List[List[str]]) -> List[str]:
    try:
        id_index = header.index("id")
    except ValueError:
        raise SubmissionError(400, "The primary CSV has no 'id' column.")
    ids = []
    for row in rows:
        value = row[id_index].strip() if id_index < len(row) else ""
        if not value:
            raise SubmissionError(400, "Every experiment needs a specimen id.")
        if not SAFE_ID_PATTERN.fullmatch(value):
            raise SubmissionError(
                400,
                f"Specimen id '{value}' cannot be used as a file name: {SAFE_ID_RULE}.",
            )
        if value in ids:
            raise SubmissionError(
                409, f"Specimen id '{value}' appears twice in the batch."
            )
        ids.append(value)
    return ids


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "batch"


def submission_message(
    title: str, contributor: Contributor, dismissed_warnings: List[str]
) -> str:
    """The commit message for a submission: the title plus its trailers."""
    return build_commit_message(
        title,
        contributor.name,
        contributor.email,
        contributor.institution,
        contributor.orcid,
        contributor.github_login,
        dismissed_warnings,
    )


async def read_provenance(
    client: DataRepoClient,
    pr_number: int,
    head_sha: str,
    branch_files: List,
) -> Optional[Provenance]:
    """Who made this submission, from the commit trailers.

    A pull request opened before trailers has none, so its committed
    ``contributions/*.json`` record answers instead. Unreadable either way
    means nobody owns it, which is a 403 rather than a free pass.
    """
    try:
        provenance = provenance_from_commits(await client.list_pull_commits(pr_number))
    except Exception:
        logger.warning("Commits of #%s could not be read", pr_number, exc_info=True)
        provenance = None
    if provenance is not None:
        return provenance

    legacy = legacy_record_path(branch_files)
    if legacy is None:
        return None
    try:
        return provenance_from_record(
            json.loads(await client.get_file_text(legacy, ref=head_sha))
        )
    except Exception:
        logger.warning("No readable provenance record at %s", legacy)
        return None


def legacy_record_path(branch_files: List) -> Optional[str]:
    """The pre-trailers ``contributions/*.json`` on the branch, if any."""
    return next((file.path for file in branch_files if file.kind == "provenance"), None)


def build_update_help(branch: str, primary_csv: str) -> List[str]:
    """How to change a submission, said where the review discussion is (#321)."""
    blob = f"https://github.com/{settings.data_repo}/blob/{branch}/{primary_csv}"
    return [
        "",
        "### To update this submission",
        "",
        "Please do not open a second submission, it would open a second pull "
        f"request. Edit [`{primary_csv}`]({blob}) on this branch, or post the "
        "corrected file in a comment and a maintainer pushes it. The checks "
        "rerun on their own.",
    ]


def _code_span(text: str) -> str:
    """Text the contributor sent, shown as is in the pull request body.

    In a code span, Markdown, links and @mentions are plain text. So a
    dismissed warning cannot ping a GitHub user, and cannot look like one of
    the `**Contributor**` lines that `_parse_pr_body` reads back (#264 H4).
    """
    one_line = " ".join(text.replace("`", "'").split())
    return f"`{one_line}`"


def build_pr_body(
    contributor: Contributor,
    input_type: Type,
    experiment_count: int,
    curve_count: int,
    dismissed_warnings: List[str],
    branch: str = "",
    primary_csv: str = "",
) -> str:
    lines = [
        "Automated submission from the RESSLab-Hub contribution editor.",
        "",
        f"- **Database**: {_type_slug(input_type)}",
        f"- **Experiments**: {experiment_count}",
        f"- **Time-series files**: {curve_count}",
        f"- **Contributor**: {contributor.name} ({contributor.email})"
        + (f", {contributor.institution}" if contributor.institution else ""),
    ]
    if contributor.orcid:
        lines.append(f"- **ORCID**: {contributor.orcid}")
    if contributor.github_login:
        # An @mention, on purpose: GitHub then notifies the contributor of
        # every comment on their own submission, and they can answer inline.
        lines.append(f"- **GitHub**: @{contributor.github_login}")
    lines += [
        "",
        "Server-side validation passed before this PR was opened.",
    ]
    if dismissed_warnings:
        lines += [
            "",
            "The contributor reviewed and dismissed these validation warnings:",
            "",
            *[f"- {_code_span(warning)}" for warning in dismissed_warnings],
        ]
    if branch and primary_csv:
        lines += build_update_help(branch, primary_csv)
    return "\n".join(lines)


#: The data repository's primary CSV is re-read from GitHub at most this often
#: per type, so the editor's automatic check can consult it on every run.
REPO_IDS_TTL_SECONDS = 300
_repo_ids_cache: Dict[Type, Tuple[float, Set[str]]] = {}


async def repo_ids(
    input_type: Type, client: Optional[DataRepoClient] = None
) -> Set[str]:
    """Specimen ids at the data repository's HEAD, cached per type."""
    cached = _repo_ids_cache.get(input_type)
    if cached and monotonic() - cached[0] < REPO_IDS_TTL_SECONDS:
        return cached[1]
    layout = _layout_for(input_type)
    client = client or DataRepoClient()
    header, rows = _read_csv(await client.get_file_text(layout.primary_csv))
    id_index = header.index("id")
    ids = {row[id_index].strip() for row in rows if id_index < len(row)}
    _repo_ids_cache[input_type] = (monotonic(), ids)
    return ids


async def flag_repo_duplicates(
    tmpdir: str,
    input_type: Type,
    results: List[ValidationResult],
    client: Optional[DataRepoClient] = None,
) -> None:
    """Flag batch ids that already exist in the data repository.

    ``submit_contribution`` refuses them (409); running the same check inside
    ``/validate`` puts the error on the id cell while the contributor is still
    editing. Catches what the database check cannot: specimens merged into the
    repository but not yet ingested. Ids the validator already reported as
    database duplicates are left alone rather than flagged twice.
    """
    layout = _layout_for(input_type)
    primary = next(
        (
            result
            for result in results
            if result.file_path.replace("\\", "/").endswith(layout.primary_csv)
        ),
        None,
    )
    if primary is None:
        return
    with open(path.join(tmpdir, layout.primary_csv), encoding="utf-8") as file:
        # csv.reader, not _read_csv: the validator numbers data rows from 1
        # including blank ones, and the errors have to land on the same rows.
        rows = list(csv.reader(io.StringIO(file.read().lstrip("\ufeff"))))
    if not rows or "id" not in rows[0]:
        return
    id_index = rows[0].index("id")
    flagged = {
        error.row for error in primary.errors if error.column == "id" and error.row
    }
    existing = await repo_ids(input_type, client)
    for row_num, row in enumerate(rows[1:], start=1):
        value = row[id_index].strip() if id_index < len(row) else ""
        if value and value in existing and row_num not in flagged:
            primary.add_error(
                row_num,
                "id",
                value,
                f"Specimen id '{value}' already exists in the data repository "
                f"(merged, awaiting ingestion) — ids must be unique.",
            )


def validate_archive(tmpdir: str, input_type: Type) -> _Layout:
    """Re-validate an extracted archive and enforce the path allowlist.

    Shared by the submit and the edit paths: both re-run the very same check
    the contributor saw in the editor before anything is committed. Errors
    block, warnings do not.
    """
    try:
        results = validate_all(input_type, [tmpdir], cpu=1, check_duplicate_ids=True)
    except NotImplementedError:
        raise SubmissionError(
            422,
            "Server-side validation is not available for this database yet, "
            "so submissions are disabled.",
        )
    if any(not result.is_valid() for result in results):
        raise SubmissionValidationFailed(results)
    return check_paths(tmpdir, input_type)


def read_batch(
    tmpdir: str, layout: _Layout
) -> Tuple[List[str], List[List[str]], List[str]]:
    """The archive's primary CSV as (header, rows, ids)."""
    primary_path = path.join(tmpdir, layout.primary_csv)
    if not path.isfile(primary_path):
        raise SubmissionError(400, "The archive has no primary CSV.")
    with open(primary_path, encoding="utf-8") as file:
        header, rows = _read_csv(file.read())
    return header, rows, batch_ids(header, rows)


def reject_clashes(ids: List[str], existing: Set[str]) -> None:
    """Refuse a batch whose ids are already in the data repository."""
    clashes = [value for value in ids if value in existing]
    if clashes:
        raise SubmissionError(
            409,
            "These specimen ids already exist in the data repository: "
            + ", ".join(clashes),
        )


def _line_terminator(text: str) -> str:
    """The file's own line endings (some repo CSVs are CRLF): rewriting them
    would turn a one-row contribution into a whole-file diff."""
    return "\r\n" if "\r\n" in text else "\n"


def build_primary_csv(
    repo_header: List[str],
    terminator: str,
    kept_rows: List[List[str]],
    header: List[str],
    rows: List[List[str]],
) -> str:
    """The repository CSV with ``kept_rows`` followed by the batch's rows.

    Align by column NAME, not position: the repo CSV's order can differ from
    the dictionary's, and it may carry legacy extras the dictionary dropped
    (e.g. hss_columns' test_id) — those get NR, and the uploader ignores them
    anyway. Only a batch column the repo lacks is real schema drift.

    Every batch row goes in as unverified, whatever the batch says: only a
    curator's verification pull request makes a row verified (#253). The
    kept rows are written back as they are.
    """
    missing = [
        name for name in header if name not in repo_header and name != STATUS_COLUMN
    ]
    if missing:
        raise SubmissionError(
            502,
            "The data repository's CSV is missing columns this contribution "
            f"provides ({', '.join(missing)}) — the data dictionary may have "
            "changed. Please contact the maintainers.",
        )

    batch_index = {name: position for position, name in enumerate(header)}

    def repo_ordered(row: List[str]) -> List[str]:
        cells = []
        for name in repo_header:
            if name == STATUS_COLUMN:
                cells.append(UNVERIFIED)
                continue
            position = batch_index.get(name)
            in_batch = position is not None and position < len(row)
            value = row[position] if in_batch else ""
            cells.append(escape_formula(value.strip() or "NR"))
        return cells

    return _write_csv(
        repo_header, kept_rows + [repo_ordered(row) for row in rows], terminator
    )


def collect_curve_files(tmpdir: str, layout: _Layout) -> List[NewFile]:
    """The archive's time-series files, ready to commit."""
    files = []
    for rel in _archive_files(tmpdir):
        if rel == layout.primary_csv or rel in layout.dictionary_csvs:
            continue
        with open(path.join(tmpdir, rel), encoding="utf-8", newline="") as file:
            files.append(NewFile(rel, normalize_csv_text(file.read())))
    return files


def commit_title(input_type: Type, ids: List[str], verb: str = "add") -> str:
    plural = "s" if len(ids) != 1 else ""
    sample = ids[0] + ("…" if len(ids) > 1 else "")
    return (
        f"data({_type_slug(input_type)}): {verb} {len(ids)} "
        f"experiment{plural} ({sample})"
    )


async def submit_contribution(
    tmpdir: str,
    input_type: Type,
    contributor: Contributor,
    dismissed_warnings: List[str],
    client: Optional[DataRepoClient] = None,
) -> SubmissionResult:
    """Validate the extracted archive and open a PR on the data repo."""
    # Server-side re-validation is the gate: errors block, warnings don't.
    # The DB duplicate check runs there too; the repo-HEAD check below is the
    # backstop for merged-but-not-yet-ingested submissions.
    layout = validate_archive(tmpdir, input_type)
    header, rows, ids = read_batch(tmpdir, layout)

    client = client or DataRepoClient()
    repo_text = await client.get_file_text(layout.primary_csv)
    repo_header, repo_rows = _read_csv(repo_text)

    id_index = repo_header.index("id")
    reject_clashes(
        ids, {row[id_index].strip() for row in repo_rows if id_index < len(row)}
    )
    merged_csv = build_primary_csv(
        repo_header, _line_terminator(repo_text), repo_rows, header, rows
    )

    files = [NewFile(layout.primary_csv, merged_csv)]
    files.extend(collect_curve_files(tmpdir, layout))
    curve_count = len(files) - 1

    suffix = secrets.token_hex(4)
    type_slug = _type_slug(input_type)
    branch = f"contrib/{type_slug}/{_slugify(ids[0])}-{suffix}"

    title = commit_title(input_type, ids)
    message = submission_message(title, contributor, dismissed_warnings)

    base_sha = await client.get_base_sha()
    commit_sha = await client.commit_files(
        branch, base_sha, files, message, contributor.name, contributor.email
    )
    try:
        pull = await client.create_pull_request(
            branch,
            title,
            build_pr_body(
                contributor,
                input_type,
                len(ids),
                curve_count,
                dismissed_warnings,
                branch,
                layout.primary_csv,
            ),
        )
    except Exception as exc:
        await client.delete_branch(branch)
        raise SubmissionError(
            502,
            "The pull request could not be opened on the data repository "
            f"({describe_error(exc)}).",
        )
    # The PR is open from here: a failure is only logged, the submit succeeds.
    await request_reviews(client, pull["number"], contributor.github_login)
    return SubmissionResult(pull["url"], pull["number"], branch, commit_sha)


async def update_contribution(
    tmpdir: str,
    pr_number: int,
    head_sha: str,
    contributor: Contributor,
    dismissed_warnings: List[str],
    client: Optional[DataRepoClient] = None,
    as_curator: bool = False,
    owner_emails: Optional[Iterable[str]] = None,
) -> SubmissionResult:
    """Replace an open submission's batch with a new commit on its branch.

    ``owner_emails`` are all the verified addresses of the account (#402),
    any of which makes the submission its own. By default only
    ``contributor.email``, the main address that the new commit records.

    The branch is made to hold exactly what the archive holds: rows rewritten,
    files added or replaced, a file the batch no longer has deleted. The pull
    request updates and its checks rerun.

    ``head_sha`` is the commit the editor loaded. A branch that moved since is
    refused (409) rather than overwritten: a maintainer may have pushed a fix.

    Only the account that made the submission can change it (403 otherwise),
    read off the commit trailers on the branch (the JSON record, for a pull
    request opened before those). A curator can change any of them
    (``as_curator``, #248): ``contributor`` is then the curator, who authors
    the commit, while the trailers and the pull request body keep naming the
    person who submitted.
    """
    client = client or DataRepoClient()
    try:
        pull = await client.get_pull(pr_number)
    except Exception:
        logger.warning("Pull request #%s could not be read", pr_number, exc_info=True)
        raise SubmissionError(
            404, "This submission does not exist on the data repository."
        )
    if pull["state"] != "open":
        raise SubmissionError(404, "This submission is closed; it cannot be changed.")
    if pull["head_sha"] != head_sha:
        raise SubmissionError(
            409,
            "This submission changed on GitHub after you opened it. Reload the "
            "page to get the latest version, then make your changes again.",
        )
    branch = pull["head_ref"]
    input_type = type_for_branch(branch)
    if input_type is None:
        raise SubmissionError(404, "This branch is not a contribution branch.")
    if from_fork(pull):
        # The commit would go to a branch of the same name on the data repo,
        # not to the fork: GitHub gives the App no write access there.
        raise SubmissionError(
            409,
            "This submission comes from a fork of the data repository. "
            "Edit it on GitHub.",
        )

    # Who made it, before any work is done on the archive.
    head_files = await client.list_pull_files(pr_number)
    # Blob sha of every file already on the branch: what the commit uses to
    # skip re-uploading the curves an edit did not touch.
    at_head = {
        file["path"]: file["sha"]
        for file in head_files
        if file.get("sha") and file.get("status") != "removed"
    }
    branch_files = classify_files(head_files, input_type)
    provenance = await read_provenance(client, pr_number, head_sha, branch_files)
    submitter = contributor
    if not owns_submission(provenance, owner_emails or (contributor.email,)):
        if not as_curator:
            raise SubmissionError(
                403,
                "This submission was made from another account. Only the person "
                "who submitted it can change it from the Hub.",
            )
        if provenance is None:
            raise SubmissionError(
                403,
                "Nothing on this branch says who submitted it, so it cannot be "
                "changed from the Hub. Change it on GitHub instead.",
            )
        submitter = Contributor(
            name=provenance.name,
            email=provenance.email,
            institution=provenance.institution,
            orcid=provenance.orcid,
            github_login=provenance.github_login,
        )

    layout = validate_archive(tmpdir, input_type)
    header, rows, ids = read_batch(tmpdir, layout)

    # Independent reads: one round trip instead of two.
    head_text, base_text = await asyncio.gather(
        client.get_file_text(layout.primary_csv, ref=head_sha),
        client.get_file_text(layout.primary_csv),
    )
    head_header, head_rows = _read_csv(head_text)
    base_header, base_rows = _read_csv(base_text)
    if "id" not in head_header or "id" not in base_header:
        raise SubmissionError(502, "The data repository's CSV has no 'id' column.")
    base_id = base_header.index("id")
    base_ids = {row[base_id].strip() for row in base_rows if base_id < len(row)}

    # Rows this submission never owned stay; its own are what the editor sends.
    kept, _ = split_batch(head_header, head_rows, base_ids)
    reject_clashes(ids, base_ids)
    merged_csv = build_primary_csv(
        head_header, _line_terminator(head_text), kept, header, rows
    )

    files = [NewFile(layout.primary_csv, merged_csv)]
    files.extend(collect_curve_files(tmpdir, layout))
    curve_count = len(files) - 1

    # Only the submission's own time-series files can be dropped: never the
    # primary CSV or anything else on the branch. A JSON record left by the old
    # code goes too, since this commit's trailers now say the same thing.
    submitted = {file.path for file in files}
    deletions = [
        file.path
        for file in branch_files
        if file.kind == "timeseries" and file.path not in submitted
    ]
    legacy = legacy_record_path(branch_files)
    if legacy is not None:
        deletions.append(legacy)

    title = commit_title(input_type, ids, verb="update")
    message = submission_message(title, submitter, dismissed_warnings)
    try:
        commit_sha = await client.commit_on_branch(
            branch,
            head_sha,
            files,
            deletions,
            message,
            contributor.name,
            contributor.email,
            existing=at_head,
        )
    except Exception:
        logger.warning("Commit on %s (#%s) failed", branch, pr_number, exc_info=True)
        raise SubmissionError(
            409,
            "The submission could not be updated: its branch moved on GitHub. "
            "Reload the page and make your changes again.",
        )
    # The review screen reads the counts off the body, so it has to follow the
    # new batch. Best effort: the data is already committed.
    try:
        await client.update_pull_body(
            pr_number,
            build_pr_body(
                submitter,
                input_type,
                len(ids),
                curve_count,
                dismissed_warnings,
                branch,
                layout.primary_csv,
            ),
        )
    except Exception:
        logger.warning("Body of #%s not refreshed", pr_number, exc_info=True)
    return SubmissionResult(pull["html_url"], pr_number, branch, commit_sha)
