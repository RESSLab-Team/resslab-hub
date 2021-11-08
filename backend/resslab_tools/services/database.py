"""
Database Service
"""
from urllib.parse import quote_plus

import databases
import sqlalchemy
from resslab_tools.config import settings
from sqlalchemy.ext.declarative import declarative_base

__username = settings.postgres_user  # type: ignore
__password = settings.postgres_password  # type: ignore
__database = settings.postgres_db  # type: ignore
__host = settings.database_host  # type: ignore
__port = settings.database_port  # type: ignore
__hostname = f'{quote_plus(__password)}@{__host}'
__url = f'postgresql://{__username}:{__hostname}:{__port}/{__database}'

database = databases.Database(__url)

engine = sqlalchemy.create_engine(__url, echo=True)

Base = declarative_base(bind=engine)
