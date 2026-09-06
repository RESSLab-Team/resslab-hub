"""
What the sign-in flows share: the clock, and the cleanup of finished rows.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from resslab_hub.models.database.auth import LoginChallenge

#: A challenge this long past its expiry is of no use to anyone. The mail cap
#: only looks one hour back, so purging older rows does not loosen it.
KEEP_FOR = timedelta(days=1)


def now() -> datetime:
    return datetime.now(timezone.utc)


def aware(value: Optional[datetime]) -> Optional[datetime]:
    """Postgres gives back tz-aware datetimes; a fresh object may not be."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


async def purge_expired(db: AsyncSession) -> None:
    """Drop old challenges. Called whenever a new one starts, which is all the
    cleanup this table needs at our scale."""
    await db.execute(
        delete(LoginChallenge).where(LoginChallenge.expires_at < now() - KEEP_FOR)
    )
