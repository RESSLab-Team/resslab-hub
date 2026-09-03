"""
Turn a validated contribution archive into a pull request on the data repo.

The archive is the same tar.gz the frontend sends to /validate: the batch's
primary CSV plus time-series files, laid out exactly like the data repository.
The flow re-validates server-side, enforces the path allowlist, appends the
batch rows to the repo's primary CSV at HEAD, and commits everything plus a
provenance record through the Git Data API.

Security invariants (epic #255): client-supplied paths are never trusted — the
only writable locations are derived here from the uploader's own type map; ids
must be safe file names (``SAFE_ID_PATTERN``, shared with the validator so the
quality check reports a bad id before submission); CSV cells that could be read as
spreadsheet formulas are prefix-escaped.
"""

import csv
import io
import json
import re
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from fnmatch import fnmatch
from hashlib import sha256
from os import path, walk
from time import monotonic
from typing import Dict, List, Optional, Set, Tuple

from resslab_hub.contributions.github import DataRepoClient, NewFile
from resslab_hub.data.common import SAFE_ID_PATTERN, SAFE_ID_RULE
from resslab_hub.data.uploader import Type, get_args_all
from resslab_hub.data.validator import ValidationResult, validate_all

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
    #: How the identity was established: the sign-in provider (``email``,
    #: ``github``), or ``self-declared`` for a submission made before #247.
    identity: str = "self-declared"
    #: Their account id, so a submission can be traced back after the fact.
    user_id: str = ""


@dataclass
class SubmissionResult:
    pr_url: str
    pr_number: int
    branch: str


class SubmissionError(Exception):
    """A submission problem with a transport status and a human-readable detail."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class SubmissionValidationFailed(Exception):
    """Server-side re-validation found errors; carries the full results."""

    def __init__(self, results: List[ValidationResult]):
        super().__init__("Validation failed")
        self.results = results


@dataclass
class _Layout:
    """Where this type's files are allowed to live, from the uploader map."""

    primary_csv: str
    curve_dirs: List[str] = field(default_factory=list)
    dictionary_csvs: List[str] = field(default_factory=list)


def _layout_for(input_type: Type) -> _Layout:
    primary_csv = None
    curve_dirs = []
    dictionary_csvs = []
    for arg_type, pattern in get_args_all(input_type, ""):
        normalized = pattern.lstrip("/")
        if arg_type is Type.DICTIONARY:
            dictionary_csvs.append(normalized)
        elif normalized.endswith("*.csv"):
            curve_dirs.append(path.dirname(normalized))
        elif primary_csv is None:
            primary_csv = normalized
    if primary_csv is None:
        raise SubmissionError(400, f"Type {input_type.value} has no primary CSV.")
    return _Layout(primary_csv, curve_dirs, dictionary_csvs)


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


def _type_slug(input_type: Type) -> str:
    return input_type.value.removeprefix("all-")


def build_provenance(
    contributor: Contributor,
    input_type: Type,
    files: List[NewFile],
    dismissed_warnings: List[str],
    submitted_at: str,
) -> str:
    return json.dumps(
        {
            "schema": 1,
            "type": input_type.value,
            "submitted_at": submitted_at,
            "contributor": {
                "name": contributor.name,
                "email": contributor.email,
                "institution": contributor.institution,
                "orcid": contributor.orcid,
                "github_login": contributor.github_login,
                # How the identity was established: the provider the
                # contributor signed in with (#247). Phase 2 replaces this with
                # why they are allowed to contribute (verified academic mail,
                # invitation, and so on).
                "identity": contributor.identity,
                "user_id": contributor.user_id,
            },
            "files": [
                {
                    "path": file.path,
                    "sha256": sha256(file.content.encode("utf-8")).hexdigest(),
                }
                for file in files
            ],
            "dismissed_warnings": dismissed_warnings,
        },
        indent=2,
    )


def build_pr_body(
    contributor: Contributor,
    input_type: Type,
    experiment_count: int,
    curve_count: int,
    dismissed_warnings: List[str],
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
            *[f"- {warning}" for warning in dismissed_warnings],
        ]
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


async def submit_contribution(
    tmpdir: str,
    input_type: Type,
    contributor: Contributor,
    dismissed_warnings: List[str],
    client: Optional[DataRepoClient] = None,
) -> SubmissionResult:
    """Validate the extracted archive and open a PR on the data repo."""
    # Server-side re-validation is the gate: errors block, warnings don't.
    # The DB duplicate check runs here too; the repo-HEAD check below is the
    # backstop for merged-but-not-yet-ingested submissions.
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

    layout = check_paths(tmpdir, input_type)

    primary_path = path.join(tmpdir, layout.primary_csv)
    if not path.isfile(primary_path):
        raise SubmissionError(400, "The archive has no primary CSV.")
    with open(primary_path, encoding="utf-8") as file:
        header, rows = _read_csv(file.read())
    ids = batch_ids(header, rows)

    client = client or DataRepoClient()
    repo_text = await client.get_file_text(layout.primary_csv)
    repo_header, repo_rows = _read_csv(repo_text)

    # Align by column NAME, not position: the repo CSV's order can differ from
    # the dictionary's, and it may carry legacy extras the dictionary dropped
    # (e.g. hss_columns' test_id) — those get NR, and the uploader ignores
    # them anyway. Only a batch column the repo lacks is real schema drift.
    missing = [name for name in header if name not in repo_header]
    if missing:
        raise SubmissionError(
            502,
            "The data repository's CSV is missing columns this contribution "
            f"provides ({', '.join(missing)}) — the data dictionary may have "
            "changed. Please contact the maintainers.",
        )

    id_index = repo_header.index("id")
    existing = {row[id_index].strip() for row in repo_rows if id_index < len(row)}
    clashes = [value for value in ids if value in existing]
    if clashes:
        raise SubmissionError(
            409,
            "These specimen ids already exist in the data repository: "
            + ", ".join(clashes),
        )

    batch_index = {name: position for position, name in enumerate(header)}

    def repo_ordered(row: List[str]) -> List[str]:
        cells = []
        for name in repo_header:
            position = batch_index.get(name)
            in_batch = position is not None and position < len(row)
            value = row[position] if in_batch else ""
            cells.append(escape_formula(value.strip() or "NR"))
        return cells

    # Keep the repo file's own line endings (some are CRLF): rewriting them
    # would turn a one-row contribution into a whole-file diff.
    terminator = "\r\n" if "\r\n" in repo_text else "\n"
    merged_csv = _write_csv(
        repo_header, repo_rows + [repo_ordered(r) for r in rows], terminator
    )

    files = [NewFile(layout.primary_csv, merged_csv)]
    curve_count = 0
    for rel in _archive_files(tmpdir):
        if rel == layout.primary_csv or rel in layout.dictionary_csvs:
            continue
        with open(path.join(tmpdir, rel), encoding="utf-8", newline="") as file:
            files.append(NewFile(rel, normalize_csv_text(file.read())))
        curve_count += 1

    submitted_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    suffix = secrets.token_hex(4)
    type_slug = _type_slug(input_type)
    branch = f"contrib/{type_slug}/{_slugify(ids[0])}-{suffix}"
    files.append(
        NewFile(
            f"contributions/{type_slug}/{suffix}.json",
            build_provenance(
                contributor, input_type, files, dismissed_warnings, submitted_at
            )
            + "\n",
        )
    )

    plural = "s" if len(ids) != 1 else ""
    sample = ids[0] + ("…" if len(ids) > 1 else "")
    title = f"data({type_slug}): add {len(ids)} experiment{plural} ({sample})"
    message = f"{title}\n\nSubmitted-by: {contributor.name} <{contributor.email}>"

    base_sha = await client.get_base_sha()
    await client.commit_files(
        branch, base_sha, files, message, contributor.name, contributor.email
    )
    try:
        pull = await client.create_pull_request(
            branch,
            title,
            build_pr_body(
                contributor, input_type, len(ids), curve_count, dismissed_warnings
            ),
        )
    except Exception:
        await client.delete_branch(branch)
        raise SubmissionError(
            502, "The pull request could not be opened on the data repository."
        )
    return SubmissionResult(pull["url"], pull["number"], branch)
