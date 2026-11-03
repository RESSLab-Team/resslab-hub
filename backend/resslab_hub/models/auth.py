"""
Request and response shapes of the ``/auth`` endpoints.

``UserOut`` is what the SPA stores as "who am I": enough to greet the person,
to show what they can do and why, and to decide which navigation entries to
render. No secret ever appears here.
"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class IdentityOut(BaseModel):
    id: str
    provider: str
    handle: str


class AccessRequestStatus(BaseModel):
    """Where the person's last access request is (#248)."""

    status: Literal["pending", "approved", "declined"]
    role: str
    created_at: datetime
    decided_at: Optional[datetime] = None


class AccessRequestIn(BaseModel):
    #: Who they are and what they want to submit.
    message: str = Field(default="", max_length=2000)


class UserOut(BaseModel):
    id: str
    email: Optional[str] = None
    email_verified: bool = False
    display_name: str = ""
    institution: str = ""
    orcid: str = ""
    role: str = "viewer"
    #: Why the role is what it is, so the account page can explain it.
    role_source: str = "default"
    github_login: str = ""
    identities: List[IdentityOut] = []
    #: The last access request, so the account page can say it is waiting.
    access_request: Optional[AccessRequestStatus] = None


class MeResponse(BaseModel):
    """``GET /auth/me``. ``user`` is null when nobody is signed in.

    Not a 401: every page load asks, and the app logs each HTTPException as an
    error. An anonymous visitor is a normal answer, not a failure.
    """

    user: Optional[UserOut] = None


class EmailStartRequest(BaseModel):
    email: EmailStr
    #: Where to go after signing in. Reduced to a path on our own site.
    redirect_to: str = "/"


class EmailStartResponse(BaseModel):
    """Always the same answer, so nobody can probe for existing accounts."""

    sent: bool = True


class EmailVerifyRequest(BaseModel):
    """Either the typed code (with the login cookie), or the mailed pair."""

    code: Optional[str] = Field(default=None, max_length=12)
    challenge: Optional[str] = None
    token: Optional[str] = None


class AddEmailRequest(BaseModel):
    """An address to add to the signed-in account (#402)."""

    email: EmailStr


class AddEmailVerifyRequest(BaseModel):
    """The code mailed to that address. The challenge is in the login cookie."""

    code: str = Field(max_length=12)


class VerifyResponse(BaseModel):
    user: UserOut
    #: Path the SPA should land on, taken from the start of the flow.
    redirect_to: str = "/"
