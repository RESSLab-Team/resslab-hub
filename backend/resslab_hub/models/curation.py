"""
Response models for the read-only curation endpoints (``/contributions`` GETs).

These project the state of open contribution pull requests on the data repo
into shapes the review interface can render. Nothing here is stored: GitHub is
the source of truth, and every field is reconstructed from the PR on demand.

The contributor's email is left out on purpose, also from the PR body that
``CurationDetail.body`` and the first ``CurationComment`` carry
(``redact_emails``): it is not needed to review a submission, and it is on the
pull request for curators who do need it.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel


class CurationContributor(BaseModel):
    name: str = ""
    institution: str = ""
    orcid: str = ""
    #: Present when the contributor linked a GitHub account (#247), so the
    #: review interface can point a curator at the person to talk to.
    github_login: str = ""


class CurationSummary(BaseModel):
    """One open pull request of the data repo, as listed in the review queue."""

    pr_number: int
    pr_url: str
    title: str
    branch: str
    #: Backend uploader ``Type`` value, e.g. ``all-braces``. Empty when the
    #: database could not be found (``kind`` is "unrecognised").
    type: str
    #: "submission": opened by the Hub, on a ``contrib/`` branch.
    #: "manual": opened by hand, the database found from its files (#267).
    #: "unrecognised": opened by hand, no single database found; ``reason``
    #: says why, and it can only be reviewed on GitHub.
    kind: str
    #: Why the database could not be found. Empty unless "unrecognised".
    reason: str
    #: From a fork of the data repo: the Hub can read it but not edit it.
    from_fork: bool
    draft: bool
    created_at: str
    updated_at: str
    #: Parsed from the PR body; ``None`` when the body format is unexpected.
    experiment_count: Optional[int] = None
    contributor: Optional[CurationContributor] = None


class CurationListResponse(BaseModel):
    #: False when the GitHub App is not configured on this deployment — the
    #: interface shows a "not enabled" empty state instead of an error.
    configured: bool
    items: List[CurationSummary] = []


class CurationFile(BaseModel):
    """One file added by the PR, classified against the type's layout."""

    path: str
    #: "primary" | "timeseries" | "provenance" | "other"
    kind: str
    #: Layout curve directory for time-series files (joins TIME_SERIES_KINDS).
    timeseries_dir: Optional[str] = None
    #: Filename stem of a time-series file — the specimen id it belongs to.
    experiment_id: Optional[str] = None


class CurationComment(BaseModel):
    """One message of a submission's discussion thread.

    Bodies are raw GitHub-flavoured markdown — the review screen renders and
    sanitizes them client-side, the same way it renders a database README.
    """

    #: GitHub comment id; 0 for the synthetic pull-request-body entry.
    id: int
    author: str
    #: GitHub account type: "User", or "Bot" for the submission App itself.
    author_type: str
    body: str
    html_url: str
    created_at: str
    updated_at: str
    #: True for the pull request body — the submission summary, shown first.
    is_body: bool


class CurationCommentsResponse(BaseModel):
    pr_number: int
    items: List[CurationComment]


class CurationExperiment(BaseModel):
    """One submitted row of the primary CSV, keyed by repo column name."""

    id: str
    #: Raw cell text; the "NR" placeholder is kept for the frontend to style.
    cells: Dict[str, str]


class CurationDetail(CurationSummary):
    """Everything the review screen needs about one submission.

    The list-ish fields carry no defaults on purpose: they are always present
    in the response, and a default would mark them optional in the OpenAPI
    schema (and therefore in the generated frontend client).
    """

    state: str
    head_sha: str
    #: PR body markdown, rendered as the submission summary.
    body: str
    submitted_at: str
    dismissed_warnings: List[str]
    #: Repo CSV header order — the stable field ordering for display.
    columns: List[str]
    experiments: List[CurationExperiment]
    files: List[CurationFile]
    #: Set when the batch could not be reconstructed faithfully (provenance
    #: unreadable, or row count differs from the PR body) — review on GitHub.
    reconstruction_warning: Optional[str]
    #: True when the signed-in account made this submission (#247), so the
    #: review screen can offer to edit it. Never cached: set per request.
    mine: bool = False
