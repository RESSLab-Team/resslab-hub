"""Response model for the ``/contributions`` endpoint."""

from pydantic import BaseModel


class ContributionResponse(BaseModel):
    """The pull request opened on the data repository for a submission."""

    pr_url: str
    pr_number: int
    branch: str
