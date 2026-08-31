"""
Shared pytest fixtures for the integration tests.

These tests need a real PostgreSQL: the uploader bulk-loads through
``COPY ... FROM STDIN`` and the API runs on asyncpg, neither of which SQLite
emulates. They run against the local dev database (``make dev-database``) using
the same credentials as the app (read from ``secrets/.env``), but the database
name is overridden to a throwaway ``resslab_hub_test`` that is created and
dropped around the test session, so the real data is never touched.
"""

import csv
import logging
import os
from pathlib import Path
from urllib.parse import quote_plus

import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# Configure settings BEFORE importing any resslab_hub module: the database name
# is swapped for the throwaway one and the startup ``alembic upgrade`` is
# disabled (we build the schema from the ORM metadata instead).
# ---------------------------------------------------------------------------
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_DIR = _BACKEND_DIR.parent

os.environ.setdefault("DOTENV_PATH_FOR_DYNACONF", str(_REPO_DIR / "secrets" / ".env"))
TEST_DB = os.environ.get("POSTGRES_TEST_DB", "resslab_hub_test")
os.environ["POSTGRES_DB"] = TEST_DB
os.environ["DATABASE_UPGRADE"] = "false"

from sqlalchemy import (  # noqa: E402
    Boolean,
    Date,
    Integer,
    Numeric,
    create_engine,
    text,
)

from resslab_hub.config import settings  # noqa: E402
from resslab_hub.data.count_flags import COUNT_FLAGS  # noqa: E402
from resslab_hub.utils.database import Base, url  # noqa: E402

# asyncpg/SQLAlchemy echo is hardcoded on; keep test output readable.
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def _maintenance_url() -> str:
    """URL to the ``postgres`` maintenance DB for CREATE/DROP DATABASE."""
    credential = f"{settings.postgres_user}:{quote_plus(settings.postgres_password)}"
    return (
        f"postgresql://{credential}"
        f"@{settings.postgres_host}:{settings.postgres_port}/postgres"
    )


@pytest.fixture(scope="session")
def _database():
    """Create the throwaway test database + schema; drop it at the end.

    Pulled in only by ``sync_engine``, so a run containing only pure-unit tests
    (the value conversions) never creates a database.
    """
    admin = create_engine(_maintenance_url(), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB}"'))
        conn.execute(text(f'CREATE DATABASE "{TEST_DB}"'))
    admin.dispose()

    # Importing the app registers every ORM table on ``Base.metadata``.
    import resslab_hub.main  # noqa: F401

    engine = create_engine(url)
    Base.metadata.create_all(engine)
    engine.dispose()

    yield

    admin = create_engine(_maintenance_url(), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(
            text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = :db AND pid <> pg_backend_pid()"
            ),
            {"db": TEST_DB},
        )
        conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB}"'))
    admin.dispose()


@pytest.fixture(scope="session")
def sync_engine(_database):
    engine = create_engine(url)
    yield engine
    engine.dispose()


@pytest.fixture
def _clean_tables(sync_engine):
    """Empty every table before a DB-touching test (requested via db_session /
    client, so pure-unit tests skip the TRUNCATE entirely)."""
    tables = ", ".join(
        f'"{table.name}"' for table in reversed(Base.metadata.sorted_tables)
    )
    with sync_engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
def db_session(sync_engine, _clean_tables):
    """A sync session for seeding fixtures and inspecting persisted rows."""
    from sqlalchemy.orm import Session

    with Session(sync_engine) as session:
        yield session


@pytest_asyncio.fixture
async def client(_clean_tables):
    """httpx client wired to the FastAPI app over the in-process ASGI app."""
    import httpx

    from resslab_hub.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as async_client:
        yield async_client
    # Dispose the module-level asyncpg engine so its pooled connections don't
    # leak across pytest-asyncio's per-test event loops (which would raise
    # InterfaceError); each client test re-acquires on its own loop.
    from resslab_hub.utils.database import engine

    await engine.dispose()


# ---------------------------------------------------------------------------
# CSV fixture helpers: build well-formed upload CSVs whose headers match the
# ORM column keys, filling every non-overridden column with a type-appropriate
# default so non-nullable columns are always populated.
# ---------------------------------------------------------------------------
def _default_for(column) -> str:
    column_type = column.type
    if isinstance(column_type, Boolean):
        return "yes"
    if isinstance(column_type, Date):
        return "01.01.20"
    if isinstance(column_type, Integer):
        return "1"
    if isinstance(column_type, Numeric):  # Float(asdecimal) subclasses Numeric
        return "1.5"
    return "x"


def write_main_csv(file_path, model, rows):
    """
    Write a main-table CSV for ``TableUploader``.

    ``rows`` is a list of dicts keyed by ORM column key; any column missing from
    a row dict is filled with a type-appropriate default.
    """
    # derived *_count flags have no header in the real CSVs either
    derived = COUNT_FLAGS.get(model, {})
    columns = [c.key for c in model.__table__.columns if c.key not in derived]
    with open(file_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        for row in rows:
            writer.writerow(
                [row.get(key, _default_for(model.__table__.c[key])) for key in columns]
            )
    return file_path


def write_measurement_csv(file_path, headers, rows):
    """Write a measurement CSV (``CsvFileUploader``) with arbitrary headers."""
    with open(file_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)
    return file_path
