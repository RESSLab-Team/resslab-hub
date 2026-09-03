"""
Signed-in browsers: the ``auth_session`` rows and the cookies that name them.

Server-side rows rather than a signed token, so signing out and (later) an
admin revoking access take effect at once, and so a role change is picked up on
the next request instead of when a token happens to expire.

Two cookies, both httpOnly and SameSite=Lax:

``resslab_session``
    the signed-in browser, 30 days, slid forward at most once an hour.
``resslab_login``
    the sign-in in progress (which challenge this browser started), 10 minutes.
    It is what makes typing the code back safe from another tab: the code alone
    is useless without it, unless the whole magic link is presented.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from resslab_hub.auth.tokens import hash_token, new_token
from resslab_hub.auth.urls import cookie_secure
from resslab_hub.config import settings
from resslab_hub.models.database.auth import Session, User

SESSION_COOKIE = "resslab_session"
LOGIN_COOKIE = "resslab_login"

#: Don't write to the sessions table on every request just to move
#: ``last_seen_at`` a few seconds.
_TOUCH_INTERVAL = timedelta(hours=1)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: Optional[datetime]) -> Optional[datetime]:
    """Postgres gives back tz-aware datetimes; a fresh object may not be."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else ""


async def create_session(
    db: AsyncSession, user: User, provider: str, request: Request
) -> str:
    """Open a session for ``user`` and return the cookie value to set."""
    token = new_token()
    ttl = timedelta(days=int(settings.session_ttl_days))
    db.add(
        Session(
            token_hash=hash_token(token),
            user_id=user.id,
            provider=provider,
            expires_at=_now() + ttl,
            last_seen_at=_now(),
            ip=_client_ip(request),
            user_agent=(request.headers.get("user-agent") or "")[:400],
        )
    )
    user.last_login_at = _now()
    await db.flush()
    return token


async def resolve_session(db: AsyncSession, token: str) -> Optional[tuple]:
    """``(session, user)`` for a cookie value, or None.

    Expired and revoked rows resolve to nothing; the expired one is deleted on
    the way past, which is all the cleanup this table needs at our scale.
    """
    if not token:
        return None
    result = await db.execute(
        select(Session, User)
        .join(User, User.id == Session.user_id)
        .where(Session.token_hash == hash_token(token))
    )
    row = result.first()
    if row is None:
        return None
    session, user = row
    if session.revoked_at is not None:
        return None
    now = _now()
    if _aware(session.expires_at) <= now:
        await db.delete(session)
        await db.commit()
        return None
    if user.disabled_at is not None:
        return None
    last_seen = _aware(session.last_seen_at)
    if last_seen is None or now - last_seen > _TOUCH_INTERVAL:
        session.last_seen_at = now
        session.expires_at = now + timedelta(days=int(settings.session_ttl_days))
        await db.commit()
    return session, user


async def revoke_session(db: AsyncSession, token: str) -> None:
    """Sign out. Idempotent: an unknown or stale cookie is not an error."""
    if not token:
        return
    result = await db.execute(
        select(Session).where(Session.token_hash == hash_token(token))
    )
    session = result.scalar_one_or_none()
    if session is not None:
        await db.delete(session)
        await db.commit()


def _set(response: Response, name: str, value: str, max_age: int) -> None:
    response.set_cookie(
        key=name,
        value=value,
        max_age=max_age,
        httponly=True,
        secure=cookie_secure(),
        # Lax, not Strict: the browser comes back from GitHub (and later from
        # the academic IdPs) on a top-level GET, which Lax allows and Strict
        # would not. Unsafe methods stay protected, and the CSRF middleware
        # checks the origin of every one of them anyway.
        samesite="lax",
        path="/",
    )


def set_session_cookie(response: Response, token: str) -> None:
    _set(
        response,
        SESSION_COOKIE,
        token,
        max_age=int(settings.session_ttl_days) * 24 * 3600,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


def set_login_cookie(response: Response, challenge_id: str) -> None:
    _set(
        response,
        LOGIN_COOKIE,
        challenge_id,
        max_age=int(settings.login_code_ttl_minutes) * 60,
    )


def clear_login_cookie(response: Response) -> None:
    response.delete_cookie(LOGIN_COOKIE, path="/")
