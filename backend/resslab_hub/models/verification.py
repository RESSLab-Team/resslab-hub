"""Request and response models of the ``/verification`` endpoints (#253)."""

from typing import List, Optional

from pydantic import BaseModel, Field

from resslab_hub.data.uploader import Type


class VerificationPull(BaseModel):
    """An open verification pull request on the data repository."""

    pr_number: int
    pr_url: str


class VerificationGroup(BaseModel):
    """Unverified rows of one database that share a reference."""

    #: Backend uploader ``Type`` value, e.g. ``all-braces``.
    database: str
    #: Empty when the rows have no reference.
    reference: str
    ids: List[str]
    count: int
    #: The open pull request that verifies these rows, if there is one. A
    #: reference with only some of its rows in one is split in two groups.
    pending_pr: Optional[VerificationPull] = None


class VerificationListResponse(BaseModel):
    #: False when the GitHub App is not configured on this deployment: the
    #: rows are still listed, but no pull request can be opened.
    configured: bool
    groups: List[VerificationGroup] = []


class VerificationRequest(BaseModel):
    #: Backend uploader ``Type`` value of a main database, e.g. ``all-braces``.
    database: Type
    ids: List[str] = Field(min_length=1)


class VerificationResponse(BaseModel):
    """The verification pull request the Hub opened."""

    pr_url: str
    pr_number: int
    branch: str
