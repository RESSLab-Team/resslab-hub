"""
What a user is allowed to do, and where that answer comes from.

Roles are ordered: ``viewer < contributor < curator < admin``. The stored
``User.role`` is the effective one; ``User.role_source`` records why, so the
account page and the admin list can explain it.

Sources, strongest first (#248). "A verified address" means any of the
account's addresses (#402), not only the main one:

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

from pyswot import find_school_names
from pyswot.vendor.stoplist import STOPLIST
from pyswot.vendor.tlds import TLDS

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
    """Domains that count as academic on top of the swot list."""
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


def _in_set(domains, labels: List[str]) -> bool:
    """swot's ``checkSet``: the domain, or one of its parents, is in the set.

    ``labels`` go from the top-level domain down (``["ch", "epfl", "sti"]``).
    """
    suffix = ""
    for label in labels:
        suffix = label + suffix
        if suffix in domains:
            return True
        suffix = "." + suffix
    return False


def _swot_academic(domain: str) -> bool:
    """swot's ``isAcademic`` (``Swot.kt``), on the data pyswot vendors.

    1. The stoplist wins, also for a subdomain: ``alumni.stanford.edu``,
       or ``glion.ch``, which is listed but stoplisted.
    2. Anything under an academic second-level domain passes
       (``edu.cn``, ``ac.za``, ``k12.ny.us``). Bare ``edu`` or ``ac.uk``
       is not one of them.
    3. Else the domain, or a parent, must be in the tree, so
       ``sti.epfl.ch`` matches ``epfl.ch``.

    Not ``pyswot.is_academic``: it also refuses a list of free mailboxes
    that swot does not have, and that list holds real universities
    (``nus.edu.sg``, ``unican.es``). swot's ``abused.txt`` is not applied
    either, like in ``Swot.kt``: JetBrains reads it on its licence form.
    """
    labels = domain.split(".")[::-1]
    if _in_set(STOPLIST, labels):
        return False
    return _in_set(TLDS, labels) or bool(find_school_names(domain))


def is_academic(email: str) -> bool:
    """True when the address belongs to a research institution.

    The JetBrains swot list (the one for student licences, see
    ``_swot_academic``) is good on universities and knows nothing of
    research institutes or industry, so ``CONTRIBUTOR_DOMAINS`` fills the
    gaps (empa.ch, aisc.org, ...). Free mailboxes are on neither.
    """
    domain = _domain_of(email)
    if not domain or "." not in domain:
        return False
    return _configured(domain) or _swot_academic(domain)


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


def verified_emails(user: User) -> List[str]:
    """Every proven address of the account, lower-cased, the main one first.

    The ``email`` identities are the proven addresses (#402). The main
    address is read too, for an account the backfill has not reached.
    """
    found: List[str] = []
    if user.email and user.email_verified_at:
        found.append(user.email.strip().lower())
    for identity in user.identities:
        if identity.provider == "email":
            address = (identity.subject or "").strip().lower()
            if address and address not in found:
                found.append(address)
    return found


def derive_role(user: User) -> tuple:
    """The role this user should have, and why. See the module docstring."""
    emails = verified_emails(user)
    admins = admin_emails()
    if any(email in admins for email in emails):
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
    if any(is_academic(email) for email in emails):
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
