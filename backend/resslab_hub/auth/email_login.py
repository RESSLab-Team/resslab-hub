"""
Sign in by mail: a six-digit code, plus a link that does the same thing.

Both are in the same mail because they cover different situations. The code
works when the mailbox is on a phone and the browser is on a laptop. The link
works when they are the same device and retyping is a nuisance.

Why the link points at the SPA and not at an endpoint: mail scanners open every
link in a message before the recipient does. A GET that consumed the token
would hand them the account, or at least burn the token. The SPA page reads the
token out of the URL and POSTs it, which no scanner does.

Guards: ten minutes, five attempts, one use, and a cap on how many mails one
address can trigger per hour. The last one is counted in SQL because the
per-IP rate limiter cannot see the address in the body, and because it has to
hold across replicas.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from resslab_hub.auth import mailer
from resslab_hub.auth.tokens import hash_token, matches, new_code, new_token
from resslab_hub.auth.urls import frontend_url, safe_redirect
from resslab_hub.auth.users import normalize_email
from resslab_hub.config import settings
from resslab_hub.models.database.auth import LoginChallenge

#: Wrong codes accepted before the challenge is dead.
MAX_ATTEMPTS = 5

#: Mails one address can trigger per hour.
MAX_MAILS_PER_HOUR = 5


class ChallengeError(Exception):
    """The code or link cannot be accepted; ``reason`` is a stable slug."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: Optional[datetime]) -> Optional[datetime]:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def verify_url(challenge_id: str, token: str) -> str:
    query = urlencode({"challenge": challenge_id, "token": token})
    return frontend_url(f"/login/verify?{query}")


async def _mails_last_hour(db: AsyncSession, email: str) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(LoginChallenge)
        .where(
            LoginChallenge.email == email,
            LoginChallenge.kind == "email",
            LoginChallenge.created_at >= _now() - timedelta(hours=1),
        )
    )
    return int(result.scalar_one())


async def start(
    db: AsyncSession,
    email: str,
    redirect_to: str = "/",
    ip: str = "",
) -> Optional[str]:
    """Create a challenge and mail it. Returns its id, or None if capped.

    The caller answers 202 either way: whether an address exists, and whether
    it has been asked for too often, are both things a stranger should not be
    able to read off the response.
    """
    email = normalize_email(email)
    if await _mails_last_hour(db, email) >= MAX_MAILS_PER_HOUR:
        return None
    code = new_code()
    token = new_token()
    challenge = LoginChallenge(
        kind="email",
        email=email,
        code_hash=hash_token(code),
        token_hash=hash_token(token),
        redirect_to=safe_redirect(redirect_to),
        ip=ip,
        expires_at=_now() + timedelta(minutes=int(settings.login_code_ttl_minutes)),
    )
    db.add(challenge)
    await db.flush()
    await db.commit()
    await mailer.send_login_mail(email, code, verify_url(challenge.id, token))
    return challenge.id


async def _load(db: AsyncSession, challenge_id: str) -> LoginChallenge:
    result = await db.execute(
        select(LoginChallenge).where(
            LoginChallenge.id == challenge_id, LoginChallenge.kind == "email"
        )
    )
    challenge = result.scalar_one_or_none()
    if challenge is None:
        raise ChallengeError("invalid_or_expired")
    if challenge.consumed_at is not None:
        raise ChallengeError("invalid_or_expired")
    if _aware(challenge.expires_at) <= _now():
        raise ChallengeError("invalid_or_expired")
    return challenge


async def verify_code(
    db: AsyncSession, challenge_id: str, code: str
) -> LoginChallenge:
    """Check a typed code against the challenge this browser started."""
    challenge = await _load(db, challenge_id)
    if challenge.attempts >= MAX_ATTEMPTS:
        raise ChallengeError("too_many_attempts")
    if not matches((code or "").strip(), challenge.code_hash or ""):
        challenge.attempts += 1
        await db.commit()
        # Say which one it is: after five wrong tries the person needs to know
        # to ask for a new mail rather than keep typing.
        if challenge.attempts >= MAX_ATTEMPTS:
            raise ChallengeError("too_many_attempts")
        raise ChallengeError("invalid_code")
    challenge.consumed_at = _now()
    await db.flush()
    return challenge


async def verify_link(db: AsyncSession, challenge_id: str, token: str) -> LoginChallenge:
    """Check the token from the mailed link. No cookie needed."""
    challenge = await _load(db, challenge_id)
    if not matches(token or "", challenge.token_hash or ""):
        challenge.attempts += 1
        await db.commit()
        raise ChallengeError("invalid_or_expired")
    challenge.consumed_at = _now()
    await db.flush()
    return challenge
