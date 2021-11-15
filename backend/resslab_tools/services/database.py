"""
Database Service
"""
from typing import AsyncIterator
from urllib.parse import quote_plus

from resslab_tools.config import settings
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

__username = settings.postgres_user  # type: ignore
__password = settings.postgres_password  # type: ignore
__database = settings.postgres_db  # type: ignore
__host = settings.database_host  # type: ignore
__port = settings.database_port  # type: ignore
__credential = f'{__username}:{quote_plus(__password)}'
__url = f'postgresql+asyncpg://{__credential}@{__host}:{__port}/{__database}'

engine = create_async_engine(__url, echo=True)

async_session = sessionmaker(engine, class_=AsyncSession)

Base = declarative_base(bind=engine)


async def async_main():
    """
    async main from
    https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)  # type: ignore
    await engine.dispose()


async def get_session() -> AsyncIterator[AsyncSession]:
    """
    Get session for FastAPI routers
    https://github.com/uriyyo/fastapi-pagination/blob/main/examples/pagination_async_sqlalchemy.py
    """
    async with async_session() as session:
        yield session
