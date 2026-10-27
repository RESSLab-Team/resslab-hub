"""
Finding and creating accounts, and attaching identities to them.

One rule runs through all of it: two identities are never merged because they
report the same address. Whoever gets there first owns the address; the second
one is told to sign in with it and link the provider from the account page.
Anything else would let an account be taken over by anyone who can make a
provider report someone else's mail.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from resslab_hub.auth import access, roles
from resslab_hub.models.database.auth import Identity, User


class IdentityTaken(Exception):
    """That provider account is already linked to a different user."""


class EmailTaken(Exception):
    """That address already belongs to a different user."""


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
    result = await db.execute(select(User).where(User.email == normalize_email(email)))
    return result.scalar_one_or_none()


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
        user = User(
            email=email,
            email_verified_at=_now(),
            display_name=name_from_email(email),
        )
        db.add(user)
        await db.flush()
    elif user.email_verified_at is None:
        user.email_verified_at = _now()
    identity = await get_identity(db, "email", email)
    if identity is None:
        db.add(Identity(user_id=user.id, provider="email", subject=email, handle=email))
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
        user_id=user.id,
        provider=provider,
        subject=str(subject),
        handle=handle,
        last_used_at=_now(),
    )
    db.add(identity)
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
    user = User(
        email=email if (email and email_verified) else None,
        email_verified_at=_now() if (email and email_verified) else None,
        display_name=display_name or handle,
    )
    db.add(user)
    await db.flush()
    db.add(
        Identity(
            user_id=user.id,
            provider=provider,
            subject=str(subject),
            handle=handle,
            last_used_at=_now(),
        )
    )
    roles.apply_role(user)
    await access.redeem_invitation(db, user)
    await db.flush()
    return user
