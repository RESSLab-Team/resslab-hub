"""
Request and response shapes of the ``/admin`` endpoints (#248).
"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr

RoleName = Literal["viewer", "contributor", "curator", "admin"]


class AdminUserOut(BaseModel):
    id: str
    email: Optional[str] = None
    email_verified: bool = False
    display_name: str = ""
    institution: str = ""
    #: Every verified address of the account, the main one first (#402).
    emails: List[str] = []
    role: str
    role_source: str
    #: The admin's own decision, if any. Null means "automatic".
    role_override: Optional[str] = None
    github_login: str = ""
    github_role: Optional[str] = None
    #: Admin from ``ADMIN_EMAILS`` or from GitHub: the Hub cannot change it.
    locked: bool = False
    created_at: datetime
    last_login_at: Optional[datetime] = None
    disabled: bool = False


class AdminUserPatch(BaseModel):
    """Only the fields that are sent change.

    ``role_override: null`` goes back to the automatic role.
    """

    role_override: Optional[RoleName] = None
    disabled: Optional[bool] = None


class AdminMergeIn(BaseModel):
    """The account to fold into the one in the path, then delete."""

    from_user_id: str


class InvitationIn(BaseModel):
    email: EmailStr
    #: Viewer is what anyone gets without an invitation.
    role: Literal["contributor", "curator", "admin"] = "contributor"


class InvitationOut(BaseModel):
    id: str
    email: str
    role: str
    status: Literal["pending", "redeemed", "revoked"]
    invited_by: str = ""
    created_at: datetime
    redeemed_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None


class InvitationCreated(InvitationOut):
    #: False when the relay failed: the invitation still works, the admin
    #: should tell the person another way.
    mailed: bool = True


class AccessRequestOut(BaseModel):
    id: str
    user_id: str
    display_name: str = ""
    email: Optional[str] = None
    institution: str = ""
    #: Their role right now, which may have changed since they asked.
    current_role: str
    role: str
    message: str = ""
    status: Literal["pending", "approved", "declined"]
    created_at: datetime
    decided_by: str = ""
    decided_at: Optional[datetime] = None
