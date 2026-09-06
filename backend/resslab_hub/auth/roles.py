"""
What a user is allowed to do, and where that answer comes from.

Roles are ordered: ``viewer < contributor < curator < admin``. The stored
``User.role`` is the effective one; ``User.role_source`` records why, so the
account page and the admin list can explain it.

Phase 1 derives from three sources only. Phase 2 (#248) adds the academic
domain check, invitations, access requests, and the curator/admin roles read
from the GitHub permission on the data repository.
"""

from typing import Iterable, List

from resslab_hub.config import settings
from resslab_hub.models.database.auth import ROLE_ORDER, User

VIEWER, CONTRIBUTOR, CURATOR, ADMIN = ROLE_ORDER


def rank(role: str) -> int:
    """Position in ``ROLE_ORDER``; an unknown role ranks lowest."""
    try:
        return ROLE_ORDER.index(role)
    except ValueError:
        return 0


def at_least(role: str, minimum: str) -> bool:
    return rank(role) >= rank(minimum)


def admin_emails() -> List[str]:
    """Addresses that become administrators at first sign-in."""
    return _split(settings.admin_emails)


def _split(raw) -> List[str]:
    if not raw:
        return []
    if isinstance(raw, str):
        parts: Iterable[str] = raw.split(",")
    else:
        parts = raw
    return [part.strip().lower() for part in parts if str(part).strip()]


def derive_role(user: User) -> tuple:
    """The role this user should have, and why.

    Order matters: an explicit admin decision wins over everything derived, in
    both directions (it can promote a company contact, or demote someone).
    """
    if user.role_override:
        return user.role_override, "override"
    verified_email = (user.email or "") if user.email_verified_at else ""
    if verified_email and verified_email.lower() in admin_emails():
        return ADMIN, "admin-email"
    # Phase 2 inserts the GitHub data-repo permission and the academic-email
    # grant here.
    return VIEWER, "default"


def apply_role(user: User) -> User:
    """Recompute and store the effective role. Call after every sign-in."""
    user.role, user.role_source = derive_role(user)
    return user
