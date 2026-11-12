"""
The OAuth ``state`` of every provider (GitHub, ORCID).

The state is a ``LoginChallenge`` row. Its id goes to the provider and in the
``resslab_login`` cookie, so the callback only works in the browser that
started the round trip. Each provider has its own ``kind``: a state started
for GitHub cannot finish on the ORCID callback.
"""

from datetime import timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from resslab_hub.auth.challenges import aware, now, purge_expired
from resslab_hub.auth.urls import safe_redirect
from resslab_hub.models.database.auth import LoginChallenge

#: An OAuth round trip is a redirect and back; ten minutes is generous.
STATE_TTL = timedelta(minutes=10)


async def start(
    db: AsyncSession,
    kind: str,
    redirect_to: str = "/",
    link_user_id: Optional[str] = None,
    ip: str = "",
) -> str:
    """Record a pending round trip; its row id is the OAuth ``state``."""
    await purge_expired(db)
    challenge = LoginChallenge(
        kind=kind,
        redirect_to=safe_redirect(redirect_to),
        link_user_id=link_user_id,
        ip=ip,
        expires_at=now() + STATE_TTL,
    )
    db.add(challenge)
    await db.commit()
    return challenge.id


async def consume_state(
    db: AsyncSession, kind: str, state: str, expected: str
) -> Optional[LoginChallenge]:
    """Look up and burn a ``state``.

    None when unknown, used, expired, of another provider, or not the one
    this browser started (``expected`` is the cookie value).
    """
    if not state or state != expected:
        return None
    result = await db.execute(
        select(LoginChallenge).where(
            LoginChallenge.id == state, LoginChallenge.kind == kind
        )
    )
    challenge = result.scalar_one_or_none()
    if (
        challenge is None
        or challenge.consumed_at is not None
        or aware(challenge.expires_at) <= now()
    ):
        return None
    challenge.consumed_at = now()
    await db.commit()
    return challenge
