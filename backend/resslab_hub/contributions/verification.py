"""
Verification pull requests (#253): a curator marks rows as verified.

A submission goes live as ``unverified``, so the lab can merge it quickly and
check the data later. Once a curator did, the Hub opens a second, small pull
request on the data repository that changes only the ``data_curation_status``
cells of those rows. It is merged on GitHub like any other (squash), and the
next upload shows the rows as verified on the site.

Like the submissions, nothing is stored in the app: an open pull request on a
``verify/<type_slug>/...`` branch is what "pending" means, and the ids it
covers are listed in its body, in an ``ids`` fenced block.
"""

import re
import secrets
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from resslab_hub.contributions.github import DataRepoClient, NewFile
from resslab_hub.contributions.projection import (
    SubmissionError,
    _layout_for,
    _type_slug,
)
from resslab_hub.contributions.submission import (
    Contributor,
    _line_terminator,
    _read_csv,
    _slugify,
    _write_csv,
    commit_title,
)
from resslab_hub.contributions.trailers import build_verification_message
from resslab_hub.data.curation_status import STATUS_COLUMN, UNVERIFIED, VERIFIED
from resslab_hub.data.uploader import Type

#: Branch prefix of a verification pull request. Not ``contrib/``, so the
#: review queue never lists one as a submission.
BRANCH_PREFIX = "verify"
#: Rows one pull request may change. A reference rarely has more than a few
#: dozen experiments; this only stops a request that makes no sense.
MAX_IDS = 500

_IDS_BLOCK = re.compile(r"```ids\r?\n(.*?)\r?\n```", re.DOTALL)
_BOM = "\ufeff"


@dataclass
class VerificationResult:
    pr_url: str
    pr_number: int
    branch: str


def type_for_verify_branch(branch: str) -> Optional[Type]:
    """``verify/<type_slug>/<name>`` -> the uploader Type, else None."""
    parts = branch.split("/")
    if len(parts) < 3 or parts[0] != BRANCH_PREFIX:
        return None
    try:
        return Type("all-" + parts[1])
    except ValueError:
        return None


def ids_from_body(body: str) -> List[str]:
    """The ids a verification pull request covers, read off its body."""
    match = _IDS_BLOCK.search(body or "")
    if match is None:
        return []
    return [line.strip() for line in match.group(1).splitlines() if line.strip()]


def pending_verifications(pulls: Iterable[dict]) -> Dict[Tuple[Type, str], dict]:
    """(type, id) -> the open verification pull request that covers it."""
    pending: Dict[Tuple[Type, str], dict] = {}
    for pull in pulls:
        input_type = type_for_verify_branch(pull.get("head_ref", ""))
        if input_type is None:
            continue
        for row_id in ids_from_body(pull.get("body", "")):
            pending.setdefault((input_type, row_id), pull)
    return pending


def clean_ids(ids: Iterable[str]) -> List[str]:
    """Stripped, without blanks or repeats, in the order given."""
    seen: List[str] = []
    for value in ids:
        text = (value or "").strip()
        if text and text not in seen:
            seen.append(text)
    return seen


def mark_verified(
    header: List[str], rows: List[List[str]], ids: List[str]
) -> List[List[str]]:
    """The rows with the status of ``ids`` set to verified, nothing else changed.

    Refuses (409) an id the file does not have, or one that is already
    verified there: the second case is a verification merged on GitHub that
    the site does not show yet, because the next upload has not run.
    """
    if "id" not in header:
        raise SubmissionError(502, "The data repository's CSV has no 'id' column.")
    if STATUS_COLUMN not in header:
        raise SubmissionError(
            502,
            f"The data repository's CSV has no '{STATUS_COLUMN}' column yet.",
        )
    id_index = header.index("id")
    status_index = header.index(STATUS_COLUMN)
    wanted = set(ids)
    found = set()
    already = []
    updated = []
    for row in rows:
        row_id = row[id_index].strip() if id_index < len(row) else ""
        if row_id not in wanted:
            updated.append(row)
            continue
        found.add(row_id)
        cells = list(row) + [""] * (len(header) - len(row))
        if cells[status_index].strip() == VERIFIED:
            already.append(row_id)
        cells[status_index] = VERIFIED
        updated.append(cells)
    unknown = [value for value in ids if value not in found]
    if unknown:
        raise SubmissionError(
            409,
            "These ids are not in the data repository: " + ", ".join(unknown),
        )
    if already:
        raise SubmissionError(
            409,
            "These ids are already verified in the data repository (the site "
            "shows it after the next upload): " + ", ".join(already),
        )
    return updated


def build_verification_body(
    curator: Contributor, input_type: Type, ids: List[str], primary_csv: str
) -> str:
    lines = [
        "Verification from the RESSLab-Hub curation page.",
        "",
        f"- **Database**: {_type_slug(input_type)}",
        f"- **Experiments**: {len(ids)}",
        f"- **Verified by**: {curator.name} ({curator.email})",
        "",
        f"It only changes the `{STATUS_COLUMN}` column of `{primary_csv}`, from "
        f"`{UNVERIFIED}` to `{VERIFIED}`. Merge it with squash, like the "
        "submissions. The site shows the rows as verified after the next upload.",
        "",
        "Ids:",
        "",
        "```ids",
        *ids,
        "```",
    ]
    return "\n".join(lines)


async def open_verification(
    input_type: Type,
    ids: List[str],
    curator: Contributor,
    pending: Optional[Dict[Tuple[Type, str], dict]] = None,
    client: Optional[DataRepoClient] = None,
) -> VerificationResult:
    """Open the pull request that marks ``ids`` of ``input_type`` as verified.

    ``pending`` is what :func:`pending_verifications` read off the open pull
    requests: an id already in one is refused (409), so two curators do not
    open the same change twice.
    """
    ids = clean_ids(ids)
    if not ids:
        raise SubmissionError(400, "Give at least one id to verify.")
    if len(ids) > MAX_IDS:
        raise SubmissionError(
            400, f"One verification can cover at most {MAX_IDS} experiments."
        )
    covered = sorted(
        {
            (row_id, (pending or {})[(input_type, row_id)]["number"])
            for row_id in ids
            if (input_type, row_id) in (pending or {})
        }
    )
    if covered:
        raise SubmissionError(
            409,
            "An open verification pull request already covers these ids: "
            + ", ".join(f"{row_id} (#{number})" for row_id, number in covered),
        )

    layout = _layout_for(input_type)
    client = client or DataRepoClient()
    # The file is read at the commit the branch starts from: read at the base
    # branch head instead, a push landing in between would be reverted by
    # this pull request's diff.
    base_sha = await client.get_base_sha()
    text = await client.get_file_text(layout.primary_csv, ref=base_sha)
    header, rows = _read_csv(text)
    updated = mark_verified(header, rows, ids)
    # `_read_csv` drops a BOM so it never sticks to the first header name.
    # Put it back, or the pull request would change the first line too.
    bom = _BOM if text.startswith(_BOM) else ""
    content = bom + _write_csv(header, updated, _line_terminator(text))

    branch = (
        f"{BRANCH_PREFIX}/{_type_slug(input_type)}/"
        f"{_slugify(ids[0])}-{secrets.token_hex(4)}"
    )
    title = commit_title(input_type, ids, verb="verify")
    message = build_verification_message(title, curator.name, curator.email)
    await client.commit_files(
        branch,
        base_sha,
        [NewFile(layout.primary_csv, content)],
        message,
        curator.name,
        curator.email,
    )
    try:
        pull = await client.create_pull_request(
            branch,
            title,
            build_verification_body(curator, input_type, ids, layout.primary_csv),
        )
    except Exception:
        await client.delete_branch(branch)
        raise SubmissionError(
            502, "The pull request could not be opened on the data repository."
        )
    return VerificationResult(pull["url"], pull["number"], branch)
