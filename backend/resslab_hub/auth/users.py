"""
Finding and creating accounts, and attaching identities to them.

One rule runs through all of it: two identities are never merged because they
report the same address. Whoever gets there first owns the address; the second
one is told to sign in with it and link the provider from the account page.
Anything else would let an account be taken over by anyone who can make a
provider report someone else's mail.

An account can still hold several addresses (#402): each one is an ``email``
identity, added from the account page with a mailed code, so the person
proved it while signed in. ``User.email`` is the main one, and one of them.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import delete, inspect, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from resslab_hub.auth import access, roles
from resslab_hub.models.database.auth import (
    AccessRequest,
    Identity,
    Invitation,
    User,
)


class IdentityTaken(Exception):
    """That provider account is already linked to a different user."""


class EmailTaken(Exception):
    """That address already belongs to a different user."""


class CannotUnlink(Exception):
    """Removing that identity would lock the account, or drop its main address."""


class CannotMerge(Exception):
    """Two accounts that an admin cannot join. ``reason`` is the API slug."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def name_from_email(email: str) -> str:
    """A first display name, so the account is not nameless before setup."""
    local = normalize_email(email).split("@", 1)[0]
    parts = [part for part in local.replace(".", " ").replace("_", " ").split() if part]
    return " ".join(part.capitalize() for part in parts) or local


async def get_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """The account holding this address, as its main one or an added one."""
    email = normalize_email(email)
    holders = select(Identity.user_id).where(
        Identity.provider == "email", Identity.subject == email
    )
    # A sub-select and not a join: a join gives one row per identity, and
    # one user would come back twice.
    result = await db.execute(
        select(User).where(or_(User.email == email, User.id.in_(holders)))
    )
    return result.scalar_one_or_none()


async def _identities(db: AsyncSession, user: User) -> list:
    """``user.identities``, loaded first if this object never had it.

    The relationship loads with every query, but not on a user built in this
    request, and an async session cannot load it lazily.
    """
    if "identities" in inspect(user).unloaded:
        await db.refresh(user, ["identities"])
    return user.identities


async def get_identity(
    db: AsyncSession, provider: str, subject: str
) -> Optional[Identity]:
    result = await db.execute(
        select(Identity).where(
            Identity.provider == provider, Identity.subject == str(subject)
        )
    )
    return result.scalar_one_or_none()


async def get_user(db: AsyncSession, user_id: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def list_identities(db: AsyncSession, user_id: str) -> list:
    result = await db.execute(
        select(Identity)
        .where(Identity.user_id == user_id)
        .order_by(Identity.created_at)
    )
    return list(result.scalars().all())


async def sign_in_with_email(db: AsyncSession, email: str) -> User:
    """The account behind a proven address, created on first sign-in.

    Proving the address is what this call means, so the address is marked
    verified and an ``email`` identity is recorded.
    """
    email = normalize_email(email)
    user = await get_by_email(db, email)
    if user is None:
        # The identity goes in with the user, so the role below can read it.
        user = User(
            email=email,
            email_verified_at=_now(),
            display_name=name_from_email(email),
            identities=[
                Identity(
                    provider="email",
                    subject=email,
                    handle=email,
                    last_used_at=_now(),
                )
            ],
        )
        db.add(user)
        await db.flush()
    else:
        if user.email == email and user.email_verified_at is None:
            user.email_verified_at = _now()
        identities = await _identities(db, user)
        identity = next(
            (
                item
                for item in identities
                if item.provider == "email" and item.subject == email
            ),
            None,
        )
        if identity is None:
            # An account from before #402 found by its main address.
            identities.append(
                Identity(
                    provider="email",
                    subject=email,
                    handle=email,
                    last_used_at=_now(),
                )
            )
        else:
            identity.last_used_at = _now()
    roles.apply_role(user)
    await access.redeem_invitation(db, user)
    await db.flush()
    return user


async def attach_identity(
    db: AsyncSession,
    user: User,
    provider: str,
    subject: str,
    handle: str,
) -> Identity:
    """Link a provider account to an existing user (the "link" flow)."""
    existing = await get_identity(db, provider, subject)
    if existing is not None:
        if existing.user_id != user.id:
            raise IdentityTaken()
        existing.handle = handle
        existing.last_used_at = _now()
        await db.flush()
        return existing
    identity = Identity(
        provider=provider,
        subject=str(subject),
        handle=handle,
        last_used_at=_now(),
    )
    (await _identities(db, user)).append(identity)
    await db.flush()
    return identity


async def sign_in_with_provider(
    db: AsyncSession,
    provider: str,
    subject: str,
    handle: str,
    email: Optional[str] = None,
    email_verified: bool = False,
    display_name: str = "",
) -> User:
    """Sign in through a non-email provider, creating the account if needed.

    ``email`` is only ever used to fill in a *new* account, and only when the
    provider says it is verified and nobody else holds it. An address already
    taken raises, and the caller tells the person to sign in with it first.
    """
    identity = await get_identity(db, provider, subject)
    if identity is not None:
        identity.handle = handle
        identity.last_used_at = _now()
        result = await db.execute(select(User).where(User.id == identity.user_id))
        user = result.scalar_one()
        roles.apply_role(user)
        await access.redeem_invitation(db, user)
        await db.flush()
        return user

    email = normalize_email(email or "")
    if email and email_verified:
        clash = await get_by_email(db, email)
        if clash is not None:
            raise EmailTaken()
    proven = bool(email and email_verified)
    identities = [
        Identity(
            provider=provider,
            subject=str(subject),
            handle=handle,
            last_used_at=_now(),
        )
    ]
    if proven:
        # The provider proved the address, so it is one of the account's
        # addresses like any other (#402).
        identities.append(Identity(provider="email", subject=email, handle=email))
    user = User(
        email=email if proven else None,
        email_verified_at=_now() if proven else None,
        display_name=display_name or handle,
        identities=identities,
    )
    db.add(user)
    await db.flush()
    roles.apply_role(user)
    await access.redeem_invitation(db, user)
    await db.flush()
    return user


async def add_email(db: AsyncSession, user: User, email: str) -> Identity:
    """Add a proven address to an account (#402).

    The caller has checked the mailed code, from this user's own session.
    Raises :class:`EmailTaken` when another account holds the address: two
    accounts are never joined. The address becomes the main one when the
    account had none (a GitHub account with a private mail).
    """
    email = normalize_email(email)
    holder = await get_by_email(db, email)
    if holder is not None and holder.id != user.id:
        raise EmailTaken()
    identities = await _identities(db, user)
    identity = next(
        (
            item
            for item in identities
            if item.provider == "email" and item.subject == email
        ),
        None,
    )
    if identity is None:
        identity = Identity(
            provider="email", subject=email, handle=email, last_used_at=_now()
        )
        identities.append(identity)
        try:
            await db.flush()
        except IntegrityError as exc:
            # Two tabs adding the same address at once. The rollback expires
            # every loaded object, so the caller must raise without reading
            # ``user`` again.
            await db.rollback()
            raise EmailTaken() from exc
    if not user.email:
        user.email = email
        user.email_verified_at = _now()
    roles.apply_role(user)
    await access.redeem_invitation(db, user)
    await db.flush()
    return identity


async def set_main_email(db: AsyncSession, user: User, identity_id: str) -> None:
    """Make one of the account's addresses the main one.

    The main address signs new submissions and gets the mails. Raises
    ``LookupError`` when the identity is not one of this user's addresses.
    """
    identities = await _identities(db, user)
    target = next(
        (
            item
            for item in identities
            if item.id == identity_id and item.provider == "email"
        ),
        None,
    )
    if target is None:
        raise LookupError(identity_id)
    user.email = target.subject
    user.email_verified_at = _now()
    roles.apply_role(user)
    await db.flush()


async def remove_identity(db: AsyncSession, user: User, identity_id: str) -> None:
    """Unlink a provider, or remove an added address.

    Raises ``LookupError`` when the identity is not this user's, and
    :class:`CannotUnlink` for the last identity (it would lock the account)
    or the main address (pick another main address first).
    """
    identities = await _identities(db, user)
    target = next((item for item in identities if item.id == identity_id), None)
    if target is None:
        raise LookupError(identity_id)
    if len(identities) <= 1:
        raise CannotUnlink()
    if target.provider == "email" and target.subject == normalize_email(
        user.email or ""
    ):
        raise CannotUnlink()
    if target.provider == "github":
        user.github_login = ""
        user.github_role = None
        user.github_role_synced_at = None
    identities.remove(target)
    await db.flush()
    # The address that made the account a contributor may be the one gone.
    roles.apply_role(user)


async def merge_users(db: AsyncSession, keep: User, other: User, admin: User) -> None:
    """Move everything of ``other`` onto ``keep``, then delete ``other``.

    Only an admin does this, from the admin page: the same person ended up
    with two accounts (an EPFL code one day, GitHub with a gmail the next).
    Every identity moves, so every address and GitHub sign in to ``keep``,
    and the submissions follow, since they belong to their addresses.
    ``other`` and its sessions are gone: that browser is signed out.

    Raises :class:`CannotMerge` for the same account twice, a disabled one
    (enable it first, so a locked-out person does not come back by the side
    door), or two different GitHub accounts (an account has one).
    """
    if keep.id == other.id:
        raise CannotMerge("same_account")
    if keep.disabled_at is not None or other.disabled_at is not None:
        raise CannotMerge("account_disabled")
    keep_ids = await _identities(db, keep)
    other_ids = await _identities(db, other)
    keep_github = {item.subject for item in keep_ids if item.provider == "github"}
    other_github = {item.subject for item in other_ids if item.provider == "github"}
    if keep_github and other_github and keep_github != other_github:
        raise CannotMerge("both_github")

    # What ``keep`` takes from ``other``, read before the row goes.
    other_email, other_verified = other.email, other.email_verified_at
    if roles.rank(other.role_override or "") > roles.rank(keep.role_override or ""):
        keep.role_override = other.role_override
    if not keep.github_login and other.github_login:
        keep.github_login = other.github_login
        keep.github_role = other.github_role
        keep.github_role_synced_at = other.github_role_synced_at
    for field in ("display_name", "institution", "address", "orcid"):
        if not getattr(keep, field) and getattr(other, field):
            setattr(keep, field, getattr(other, field))
    if other.last_login_at and (
        keep.last_login_at is None or other.last_login_at > keep.last_login_at
    ):
        keep.last_login_at = other.last_login_at

    # One open access request per person: the second one is closed.
    if await _pending_request(db, keep.id) is not None:
        await db.execute(
            update(AccessRequest)
            .where(AccessRequest.user_id == other.id, AccessRequest.status == "pending")
            .values(status="declined", decided_by=admin.id, decided_at=_now())
        )
    moves = (
        (Identity, Identity.user_id),
        (AccessRequest, AccessRequest.user_id),
        (AccessRequest, AccessRequest.decided_by),
        (Invitation, Invitation.invited_by),
        (Invitation, Invitation.redeemed_by),
    )
    for table, column in moves:
        await db.execute(
            update(table)
            .where(column == other.id)
            .values({column.key: keep.id})
            .execution_options(synchronize_session=False)
        )
    # Sessions and sign-ins in progress go with the row (ON DELETE CASCADE).
    # The loaded ``other`` (and, by cascade, its loaded identities, whose
    # ``user_id`` is stale now) leave the session first, so the ORM neither
    # deletes those identities nor writes the old row back.
    db.expunge(other)
    await db.execute(
        delete(User)
        .where(User.id == other.id)
        .execution_options(synchronize_session=False)
    )
    # The address can only move once the other row is gone: it is unique.
    if not keep.email and other_email:
        keep.email = other_email
        keep.email_verified_at = other_verified
    await db.refresh(keep, ["identities"])
    roles.apply_role(keep)
    await access.redeem_invitation(db, keep)
    await db.flush()


async def _pending_request(db: AsyncSession, user_id: str) -> Optional[AccessRequest]:
    result = await db.execute(
        select(AccessRequest).where(
            AccessRequest.user_id == user_id, AccessRequest.status == "pending"
        )
    )
    return result.scalar_one_or_none()
