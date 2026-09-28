"""
Model definitions
"""

from pydantic import BaseModel


class Info(BaseModel):
    """
    App Info
    """

    name: str
    version: str


class Features(BaseModel):
    """
    What this deployment offers, read once by the frontend at start.
    """

    #: Submit, curation, sign-in and account: CONTRIBUTIONS_ENABLED and a
    #: GitHub App to open the pull requests.
    contributions: bool
