"""
What a user is allowed to do, and where that answer comes from.

Roles are ordered: ``viewer < contributor < curator < admin``. The stored
``User.role`` is the effective one; ``User.role_source`` records why, so the
account page and the admin list can explain it.

Sources, strongest first (#248):

1. a verified address in ``ADMIN_EMAILS``: admin;
2. admin on the data repository, through the linked GitHub account: admin;
3. an admin's decision in the Hub (``role_override``), which is also what an
   approved access request or a redeemed invitation writes;
4. write (or maintain) on the data repository: curator;
5. an academic email address: contributor, the right to submit;
6. else viewer.

The first two are above the override on purpose: nobody can demote, from the
Hub, an admin that GitHub or the config made. Change it there instead.
"""

from typing import Iterable, List, Optional

import pyswot

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


def contributor_domains() -> List[str]:
    """Domains that count as academic on top of the pyswot list."""
    return _split(settings.contributor_domains)


def _domain_of(email: str) -> str:
    # Not users.normalize_email: that module imports this one.
    return (email or "").strip().lower().rpartition("@")[2]


def _configured(domain: str) -> bool:
    """``lab.empa.ch`` matches a configured ``empa.ch``.

    Stops before the last label, so a lone ``ch`` in the setting can never
    hand the role to a whole country.
    """
    allowed = contributor_domains()
    if not allowed:
        return False
    labels = domain.split(".")
    return any(".".join(labels[index:]) in allowed for index in range(len(labels) - 1))


def is_academic(email: str) -> bool:
    """True when the address belongs to a research institution.

    pyswot carries the list JetBrains uses for student licences: free
    mailboxes never pass, a stoplist of abused domains is refused, and the
    rest must be listed (a subdomain matches its parent). The list is good
    on universities and knows nothing of research institutes or industry,
    so ``CONTRIBUTOR_DOMAINS`` fills the gaps (empa.ch, aisc.org, ...).
    """
    domain = _domain_of(email)
    if not domain or "." not in domain:
        return False
    return _configured(domain) or bool(pyswot.is_academic(domain))


def _split(raw) -> List[str]:
    if not raw:
        return []
    if isinstance(raw, str):
        parts: Iterable[str] = raw.split(",")
    else:
        parts = raw
    return [part.strip().lower() for part in parts if str(part).strip()]


#: GitHub's base permission on the data repo, and the role it grants.
#: ``read`` and ``none`` grant nothing.
GITHUB_ROLES = {"admin": ADMIN, "write": CURATOR}


def github_permission_to_role(permission: Optional[str]) -> Optional[str]:
    return GITHUB_ROLES.get((permission or "").lower())


def _verified_email(user: User) -> str:
    return (user.email or "") if user.email_verified_at else ""


def derive_role(user: User) -> tuple:
    """The role this user should have, and why. See the module docstring."""
    verified_email = _verified_email(user)
    if verified_email and verified_email.lower() in admin_emails():
        return ADMIN, "admin-email"
    from_github = (
        github_permission_to_role(user.github_role) if user.github_login else None
    )
    if from_github == ADMIN:
        return ADMIN, "github"
    if user.role_override:
        return user.role_override, "override"
    if from_github == CURATOR:
        return CURATOR, "github"
    if verified_email and is_academic(verified_email):
        return CONTRIBUTOR, "academic-email"
    return VIEWER, "default"


def is_locked_admin(user: User) -> bool:
    """Admin from ``ADMIN_EMAILS`` or from GitHub: the Hub cannot change it."""
    return derive_role(user) in ((ADMIN, "admin-email"), (ADMIN, "github"))


def apply_role(user: User) -> User:
    """Recompute and store the effective role.

    Call after anything that changes one of the sources: a sign-in, a GitHub
    sync, an admin decision.
    """
    user.role, user.role_source = derive_role(user)
    return user
