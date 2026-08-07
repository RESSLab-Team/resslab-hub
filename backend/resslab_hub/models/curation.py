"""
Response models for the read-only curation endpoints (``/contributions`` GETs).

These project the state of open contribution pull requests on the data repo
into shapes the review interface can render. Nothing here is stored: GitHub is
the source of truth, and every field is reconstructed from the PR on demand.

The contributor's email is deliberately omitted — the endpoints are
unauthenticated until #247, and the address is visible on GitHub for curators
who need it.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel


class CurationContributor(BaseModel):
    name: str = ""
    institution: str = ""
    orcid: str = ""


class CurationSummary(BaseModel):
    """One open contribution PR, as listed in the review queue."""

    pr_number: int
    pr_url: str
    title: str
    branch: str
    #: Backend uploader ``Type`` value, e.g. ``all-braces``.
    type: str
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


class CurationExperiment(BaseModel):
    """One submitted row of the primary CSV, keyed by repo column name."""

    id: str
    #: Raw cell text; the "NR" placeholder is kept for the frontend to style.
    cells: Dict[str, str]


class CurationDetail(CurationSummary):
    """Everything the review screen needs about one submission."""

    state: str
    head_sha: str
    #: PR body markdown, rendered as the submission summary.
    body: str
    submitted_at: str = ""
    dismissed_warnings: List[str] = []
    #: Repo CSV header order — the stable field ordering for display.
    columns: List[str] = []
    experiments: List[CurationExperiment] = []
    files: List[CurationFile] = []
    #: Set when the batch could not be reconstructed faithfully (provenance
    #: unreadable, or row count differs from the PR body) — review on GitHub.
    reconstruction_warning: Optional[str] = None
