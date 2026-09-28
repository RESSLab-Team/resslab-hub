"""
Signed-in browsers: the ``auth_session`` rows and the cookies that name them.

Server-side rows rather than a signed token, so signing out and (later) an
admin revoking access take effect at once.

Two cookies, both httpOnly and SameSite=Lax:

``resslab_session``
    the signed-in browser, 30 days.
``resslab_login``
    a sign-in in progress (the mailed challenge, or the GitHub ``state``), ten
    minutes. It ties the second step to the browser that did the first, so a
    code or a callback URL is useless anywhere else.

Lax, not Strict, because the browser comes back from GitHub on a top-level
GET, which Lax allows. Unsafe methods are covered by the CSRF middleware.
"""

from datetime import timedelta
from typing import Optional

from fastapi import Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from resslab_hub.auth.challenges import aware, now
from resslab_hub.auth.tokens import hash_token, new_token
from resslab_hub.auth.urls import cookie_secure
from resslab_hub.config import settings
from resslab_hub.models.database.auth import Session, User

SESSION_COOKIE = "resslab_session"
LOGIN_COOKIE = "resslab_login"

#: ``last_seen_at`` is moved at most this often, not on every request.
_TOUCH_INTERVAL = timedelta(hours=1)


def client_ip(request: Request) -> str:
    return request.client.host if request.client else ""


async def create_session(
    db: AsyncSession, user: User, provider: str, request: Request
) -> str:
    """Open a session for ``user`` and return the cookie value to set."""
    token = new_token()
    db.add(
        Session(
            token_hash=hash_token(token),
            user_id=user.id,
            provider=provider,
            expires_at=now() + timedelta(days=int(settings.session_ttl_days)),
            last_seen_at=now(),
            ip=client_ip(request),
            user_agent=(request.headers.get("user-agent") or "")[:400],
        )
    )
    user.last_login_at = now()
    await db.flush()
    return token


async def resolve_session(db: AsyncSession, token: str) -> Optional[tuple]:
    """``(session, user)`` for a cookie value, or None.

    Expired and revoked rows resolve to nothing; an expired one is deleted on
    the way past.
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
    if session.revoked_at is not None or user.disabled_at is not None:
        return None
    current = now()
    if aware(session.expires_at) <= current:
        await db.delete(session)
        await db.commit()
        return None
    last_seen = aware(session.last_seen_at)
    if last_seen is None or current - last_seen > _TOUCH_INTERVAL:
        session.last_seen_at = current
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
        samesite="lax",
        path="/",
    )


def set_session_cookie(response: Response, token: str) -> None:
    _set(response, SESSION_COOKIE, token, int(settings.session_ttl_days) * 86400)


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


def set_login_cookie(response: Response, challenge_id: str) -> None:
    _set(
        response, LOGIN_COOKIE, challenge_id, int(settings.login_code_ttl_minutes) * 60
    )


def clear_login_cookie(response: Response) -> None:
    response.delete_cookie(LOGIN_COOKIE, path="/")
