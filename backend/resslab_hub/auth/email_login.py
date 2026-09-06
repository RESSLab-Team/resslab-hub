"""
Sign in by mail: a six-digit code, plus a link that does the same thing.

The code is for when the mailbox is on another device; the link for when it is
the same one. The link points at the SPA, not at an endpoint: mail scanners
open every link before the recipient does, and a GET that consumed the token
would burn it. The page reads the token out of the URL and POSTs it.

Guards: ten minutes, five attempts, one use, and caps on how many mails one
address and one IP can trigger per hour. The caps are counted in SQL because
the rate limiter cannot see the address, and because they must hold across
replicas.
"""

from datetime import timedelta
from typing import Optional
from urllib.parse import urlencode

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from resslab_hub.auth import mailer
from resslab_hub.auth.challenges import aware, now, purge_expired
from resslab_hub.auth.tokens import hash_token, matches, new_code, new_token
from resslab_hub.auth.urls import frontend_url, safe_redirect
from resslab_hub.auth.users import normalize_email
from resslab_hub.config import settings
from resslab_hub.models.database.auth import LoginChallenge

#: Wrong codes accepted before the challenge is dead.
MAX_ATTEMPTS = 5

#: Mails one address can trigger per hour.
MAX_MAILS_PER_HOUR = 5

#: Mails one IP can trigger per hour, whatever the addresses. This is what
#: keeps a stranger from using the EPFL relay to spam a list of people.
MAX_MAILS_PER_HOUR_PER_IP = 20


class ChallengeError(Exception):
    """The code or link cannot be accepted; ``reason`` is a stable slug."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def verify_url(challenge_id: str, token: str) -> str:
    query = urlencode({"challenge": challenge_id, "token": token})
    return frontend_url(f"/login/verify?{query}")


async def _sent_last_hour(db: AsyncSession, **by) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(LoginChallenge)
        .filter_by(kind="email", **by)
        .where(LoginChallenge.created_at >= now() - timedelta(hours=1))
    )
    return int(result.scalar_one())


async def start(
    db: AsyncSession,
    email: str,
    redirect_to: str = "/",
    ip: str = "",
) -> Optional[str]:
    """Create a challenge and mail it. Returns its id, or None if capped.

    The caller answers the same way either way: whether an address exists, and
    whether it has been asked for too often, are not a stranger's business.
    """
    email = normalize_email(email)
    await purge_expired(db)
    if await _sent_last_hour(db, email=email) >= MAX_MAILS_PER_HOUR:
        return None
    if ip and await _sent_last_hour(db, ip=ip) >= MAX_MAILS_PER_HOUR_PER_IP:
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
        expires_at=now() + timedelta(minutes=int(settings.login_code_ttl_minutes)),
    )
    db.add(challenge)
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
    if (
        challenge is None
        or challenge.consumed_at is not None
        or aware(challenge.expires_at) <= now()
    ):
        raise ChallengeError("invalid_or_expired")
    return challenge


async def _count_failure(db: AsyncSession, challenge: LoginChallenge) -> int:
    """Add one attempt in SQL, so two parallel tries cannot both count as one."""
    result = await db.execute(
        update(LoginChallenge)
        .where(LoginChallenge.id == challenge.id)
        .values(attempts=LoginChallenge.attempts + 1)
        .returning(LoginChallenge.attempts)
    )
    attempts = int(result.scalar_one())
    await db.commit()
    return attempts


async def verify_code(db: AsyncSession, challenge_id: str, code: str) -> LoginChallenge:
    """Check a typed code against the challenge this browser started."""
    challenge = await _load(db, challenge_id)
    if challenge.attempts >= MAX_ATTEMPTS:
        raise ChallengeError("too_many_attempts")
    if not matches((code or "").strip(), challenge.code_hash or ""):
        # Say which one it is: after the last try the person needs to know to
        # ask for a new mail rather than keep typing.
        if await _count_failure(db, challenge) >= MAX_ATTEMPTS:
            raise ChallengeError("too_many_attempts")
        raise ChallengeError("invalid_code")
    challenge.consumed_at = now()
    await db.flush()
    return challenge


async def verify_link(
    db: AsyncSession, challenge_id: str, token: str
) -> LoginChallenge:
    """Check the token from the mailed link. No cookie needed."""
    challenge = await _load(db, challenge_id)
    if not matches(token or "", challenge.token_hash or ""):
        await _count_failure(db, challenge)
        raise ChallengeError("invalid_or_expired")
    challenge.consumed_at = now()
    await db.flush()
    return challenge
