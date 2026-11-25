"""
Submission provenance, written in the commit message as git trailers.

Who submitted a batch, from where, and which validation warnings they dismissed
describe a *change*, not the data, so they live where git already keeps that
kind of thing: key/value trailers in the last paragraph of the commit message,
the same mechanism as ``Signed-off-by`` or ``Co-authored-by``.

They also survive where a file does not. The data repo squash-merges with
"PR title + commit messages", and GitHub makes the App the author of the squash
commit, so on ``main`` the trailers are the only trace of the contributor left.

Submissions opened before this change committed a ``contributions/<type>/<x>.json``
record instead. ``provenance_from_record`` reads those, so an open pull request
made by the old code keeps working.
"""

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Union

from enacit4r_contrib.trailers import address, format_trailers, split_address
from enacit4r_contrib.trailers import parse_trailers as library_parse_trailers

#: Who submitted, and the address ownership is checked against.
SUBMITTED_BY = "Submitted-by"
INSTITUTION = "Institution"
ORCID = "ORCID"
GITHUB = "GitHub"
#: One per warning the contributor reviewed and dismissed before submitting.
DISMISSED_WARNING = "Dismissed-Warning"
#: The curator who checked the rows of a verification pull request (#253).
VERIFIED_BY = "Verified-by"


@dataclass
class Provenance:
    """Who made a submission, however it was recorded."""

    name: str = ""
    email: str = ""
    institution: str = ""
    orcid: str = ""
    github_login: str = ""
    #: When the submission was first opened (ISO-8601).
    submitted_at: str = ""
    dismissed_warnings: List[str] = field(default_factory=list)


def _one_line(value: str) -> str:
    """A trailer value holds one line, so fold any whitespace into spaces."""
    return " ".join(str(value or "").split())


def build_commit_message(
    title: str,
    name: str,
    email: str,
    institution: str = "",
    orcid: str = "",
    github_login: str = "",
    dismissed_warnings: Optional[List[str]] = None,
) -> str:
    """The commit message for a submission: title, blank line, trailers.

    Empty fields are left out rather than written empty, so the message says
    only what is known.
    """
    login = _one_line(github_login)
    return format_trailers(
        _one_line(title),
        [
            (SUBMITTED_BY, address(_one_line(name), _one_line(email))),
            (INSTITUTION, _one_line(institution)),
            (ORCID, _one_line(orcid)),
            (GITHUB, f"@{login.lstrip('@')}" if login else ""),
            *((DISMISSED_WARNING, _one_line(w)) for w in dismissed_warnings or []),
        ],
    )


def build_verification_message(title: str, name: str, email: str) -> str:
    """The commit message of a verification pull request: title, blank line,
    who checked the data. It has no ``Submitted-by``, so nothing reads it as a
    submission."""
    return format_trailers(
        _one_line(title), [(VERIFIED_BY, address(_one_line(name), _one_line(email)))]
    )


def parse_trailers(message: str) -> Dict[str, List[str]]:
    """The trailers of a commit message, keyed by name, values in order.

    Only the last paragraph is read, and only when every one of its lines is a
    trailer: that is how git tells a trailer block from a prose paragraph that
    happens to contain a colon.
    """
    return library_parse_trailers(message or "")


def _first(trailers: Dict[str, List[str]], key: str) -> str:
    values = trailers.get(key) or []
    return values[0] if values else ""


def provenance_from_commits(commits: List[dict]) -> Optional[Provenance]:
    """Read a branch's provenance off its commits.

    A commit made by the Hub carries ``Submitted-by``. Who owns the submission
    comes from the **first** one, so a later push cannot take it over. The
    dismissed warnings come from the **last** one, since an update sends the
    batch, and its warnings, again.

    ``None`` when no commit carries the trailer: either not a Hub submission,
    or one made before trailers (the caller then falls back to the JSON).
    """
    hub_commits = []
    for commit in commits or []:
        trailers = parse_trailers(commit.get("message", ""))
        if trailers.get(SUBMITTED_BY):
            hub_commits.append((commit, trailers))
    if not hub_commits:
        return None

    first_commit, first = hub_commits[0]
    _, last = hub_commits[-1]
    name, email = split_address(_first(first, SUBMITTED_BY))
    return Provenance(
        name=name,
        email=email,
        institution=_first(first, INSTITUTION),
        orcid=_first(first, ORCID),
        github_login=_first(first, GITHUB).lstrip("@"),
        submitted_at=str(first_commit.get("author_date") or ""),
        dismissed_warnings=list(last.get(DISMISSED_WARNING) or []),
    )


def provenance_from_record(record: Optional[dict]) -> Optional[Provenance]:
    """The same shape, read from a pre-trailers ``contributions/*.json``."""
    if not isinstance(record, dict):
        return None
    who = record.get("contributor")
    if not isinstance(who, dict):
        who = {}
    dismissed = record.get("dismissed_warnings")
    return Provenance(
        name=str(who.get("name") or ""),
        email=str(who.get("email") or ""),
        institution=str(who.get("institution") or ""),
        orcid=str(who.get("orcid") or ""),
        github_login=str(who.get("github_login") or "").lstrip("@"),
        submitted_at=str(record.get("submitted_at") or ""),
        dismissed_warnings=(
            [str(w) for w in dismissed] if isinstance(dismissed, list) else []
        ),
    )


def owns_submission(
    provenance: Optional[Provenance], emails: Union[str, Iterable[str]]
) -> bool:
    """Whether the account may change the submission ``provenance`` describes.

    The recorded address decides, which is what the account's verified
    addresses prove. ``emails`` is one address or all of the account's: a
    submission made from any of them is the account's (#402). Nothing
    readable means nobody owns it (#248).
    """
    if provenance is None:
        return False
    recorded = provenance.email.strip().lower()
    if isinstance(emails, str):
        emails = (emails,)
    return bool(recorded) and recorded in {
        (email or "").strip().lower() for email in emails
    }
