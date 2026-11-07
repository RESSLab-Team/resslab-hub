"""
Database Service
"""

from typing import AsyncIterator
from urllib.parse import quote_plus

from alembic.command import upgrade
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from resslab_hub.config import settings

__username: str = settings.postgres_user  # type: ignore
__password: str = settings.postgres_password  # type: ignore
__database: str = settings.postgres_db  # type: ignore
__host: str = settings.postgres_host  # type: ignore
__port: str = settings.postgres_port  # type: ignore
__credential = f"{__username}:{quote_plus(__password)}"
__url_without_driver = f"://{__credential}@{__host}:{__port}/{__database}"
url = "postgresql" + __url_without_driver
async_url = "postgresql+asyncpg" + __url_without_driver

engine = create_async_engine(
    async_url,
    echo=settings.get("sql_echo", False),
    pool_size=settings.get("db_pool_size", 5),
    max_overflow=settings.get("db_max_overflow", 10),
    pool_pre_ping=True,
    pool_recycle=1800,
)

# expire_on_commit=False, the recommended setting for AsyncSession: with the
# default, reading any attribute after a commit triggers a lazy refresh, which
# an async session cannot do outside its greenlet and which raises
# MissingGreenlet. Only the sign-in code commits through this maker; the
# uploader has its own sync session.
async_session = sessionmaker(  # type: ignore
    engine, class_=AsyncSession, expire_on_commit=False
)


# qualify the base with __allow_unmapped__.
class BaseUnmapped:
    __allow_unmapped__ = True


Base = declarative_base(cls=BaseUnmapped)


def upgrade_database():
    """
    Run database migration with alembic
    https://alembic.sqlalchemy.org/en/latest/api/commands.html
    """
    alembic_cfg = Config("alembic.ini")
    upgrade(alembic_cfg, "head")


async def get_session() -> AsyncIterator[AsyncSession]:
    """
    Get session for FastAPI routers
    https://github.com/uriyyo/fastapi-pagination/blob/main/examples/pagination_async_sqlalchemy.py
    """
    async with async_session() as session:
        yield session
