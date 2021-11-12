"""
Database Service
"""
from typing import AsyncIterator
from urllib.parse import quote_plus

import sqlalchemy
from resslab_tools.config import settings
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

__username = settings.postgres_user  # type: ignore
__password = settings.postgres_password  # type: ignore
__database = settings.postgres_db  # type: ignore
__host = settings.database_host  # type: ignore
__port = settings.database_port  # type: ignore
__hostname = f'{quote_plus(__password)}@{__host}'
__url = f'postgresql+asyncpg://{__username}:{__hostname}:{__port}/{__database}'

metadata = sqlalchemy.MetaData()

engine = create_async_engine(__url, echo=True)

async_session = sessionmaker(engine, class_=AsyncSession)

Base = declarative_base(bind=engine)


async def get_session() -> AsyncIterator[AsyncSession]:
    """
    Get session for FastAPI routers
    https://github.com/uriyyo/fastapi-pagination/blob/main/examples/pagination_async_sqlalchemy.py
    """
    async with async_session() as session:
        yield session
