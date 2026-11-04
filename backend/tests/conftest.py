"""
Shared pytest fixtures for the integration tests.

These tests need a real PostgreSQL: the uploader bulk-loads through
``COPY ... FROM STDIN`` and the API runs on asyncpg, neither of which SQLite
emulates. They run against the local dev database (``make dev-database``) using
the same credentials as the app (read from ``secrets/.env``), but the database
name is overridden to a throwaway ``resslab_hub_test`` that is created and
dropped around the test session, so the real data is never touched. CONNECT on
it is revoked from PUBLIC, so only the role that created it can connect.
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
from resslab_hub.data.curation_status import STATUS_COLUMN, VERIFIED  # noqa: E402
from resslab_hub.utils.database import Base, url  # noqa: E402

# asyncpg/SQLAlchemy echo is hardcoded on; keep test output readable.
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def _maintenance_url() -> str:
    """URL of the DB that CREATE/DROP DATABASE are issued from.

    ``postgres`` by default. In a worktree the login is a role that can only
    connect to its own branch clone, so ``wt-db.sh`` sets
    ``POSTGRES_MAINTENANCE_DB`` to that clone.
    """
    credential = f"{settings.postgres_user}:{quote_plus(settings.postgres_password)}"
    return (
        f"postgresql://{credential}"
        f"@{settings.postgres_host}:{settings.postgres_port}"
        f"/{settings.postgres_maintenance_db}"
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
        # Same as wt-db.sh does for the branch clone: only the owner connects.
        conn.execute(text(f'REVOKE CONNECT ON DATABASE "{TEST_DB}" FROM PUBLIC'))
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
# Sign-in helpers (#247)
#
# Auth is enforced by FastAPI dependencies, which only run over HTTP. So the
# gated endpoints have to be exercised through the ``client`` fixture, and a
# test that needs a signed-in caller seeds a user plus a session row and sets
# the cookie by hand, the same thing a real sign-in ends up doing.
# ---------------------------------------------------------------------------
# Whatever the environment configured: settings.toml [development] says
# "changeit", CI says something else.
SERVICE_AUTH = (str(settings.api_username), str(settings.api_password))


@pytest.fixture
def sign_in(client, db_session):
    """Sign ``client`` in as a new user; returns the ``User`` row.

    ``sign_in()`` for a plain account, ``sign_in(role="curator")`` to skip
    straight to a role, plus anything else to set on the user.

    Every verified address is an ``email`` identity, like in the app (#402):
    the main one when ``verified``, plus each of ``emails``. A GitHub or
    unverified account gets a GitHub identity instead, so it has one.
    """
    from resslab_hub.auth.tokens import hash_token, new_token
    from resslab_hub.models.database.auth import Identity, Session, User

    created = []

    def _sign_in(
        email: str = "ada@example.edu",
        role: str = "viewer",
        provider: str = "email",
        verified: bool = True,
        emails=(),
        **fields,
    ):
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        user = User(
            email=email,
            email_verified_at=now if verified else None,
            display_name=fields.pop("display_name", "Ada Lovelace"),
            institution=fields.pop("institution", "EPFL"),
            role=role,
            **fields,
        )
        db_session.add(user)
        db_session.flush()
        addresses = [email] if (provider == "email" and verified) else []
        addresses += [address.lower() for address in emails]
        for address in addresses:
            db_session.add(
                Identity(
                    user_id=user.id, provider="email", subject=address, handle=address
                )
            )
        if provider != "email" or not verified:
            db_session.add(
                Identity(
                    user_id=user.id,
                    provider="github",
                    subject=str(90000 + len(created)),
                    handle=fields.get("github_login") or "ada",
                )
            )
        token = new_token()
        db_session.add(
            Session(
                token_hash=hash_token(token),
                user_id=user.id,
                provider=provider,
                created_at=now,
                expires_at=now + timedelta(days=30),
                last_seen_at=now,
            )
        )
        db_session.commit()
        client.cookies.set("resslab_session", token)
        created.append(user)
        return user

    yield _sign_in
    client.cookies.clear()


@pytest.fixture(autouse=True)
def _no_github_permission_reads(monkeypatch):
    """No test reads a permission from GitHub, whatever ``secrets/.env`` says.

    The role sync (#248) only asks GitHub when the App is configured, and a
    developer's ``.env`` may well configure it.
    """
    from resslab_hub.auth import github_sync

    monkeypatch.setattr(github_sync, "configured", lambda: False)


@pytest.fixture
def github_permissions(monkeypatch):
    """GitHub permissions on the data repo, by login, without calling GitHub.

    ``github_permissions["ada-l"] = "write"`` makes ``@ada-l`` a curator at
    the next sync. A login missing from the dict has ``none``; an exception
    as the value is raised, like a GitHub outage.
    """
    from resslab_hub.auth import github_sync

    permissions = {}

    class _FakeClient:
        async def get_permission(self, login):
            value = permissions.get(login, "none")
            if isinstance(value, Exception):
                raise value
            return value

    monkeypatch.setattr(github_sync, "configured", lambda: True)
    monkeypatch.setattr(github_sync, "DataRepoClient", _FakeClient)
    return permissions


# ---------------------------------------------------------------------------
# CSV fixture helpers: build well-formed upload CSVs whose headers match the
# ORM column keys, filling every non-overridden column with a type-appropriate
# default so non-nullable columns are always populated.
# ---------------------------------------------------------------------------
def _default_for(column) -> str:
    if column.key == STATUS_COLUMN:  # a word from a short list, not free text
        return VERIFIED
    column_type = column.type
    if isinstance(column_type, Boolean):
        return "yes"
    if isinstance(column_type, Date):
        return "01.01.2020"
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
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(columns)
        for row in rows:
            writer.writerow(
                [row.get(key, _default_for(model.__table__.c[key])) for key in columns]
            )
    return file_path


def write_measurement_csv(file_path, headers, rows):
    """Write a measurement CSV (``CsvFileUploader``) with arbitrary headers."""
    with open(file_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(headers)
        writer.writerows(rows)
    return file_path


def github_refusal(status_code, body):
    """The error githubkit raises when GitHub answers ``status_code``.

    ``body`` is a dict for GitHub's usual JSON, or a string for anything else
    (a proxy's HTML page).
    """
    import httpx
    from githubkit.exception import RequestFailed
    from githubkit.response import Response

    request = httpx.Request("POST", "https://api.github.com/repos/o/r/git/blobs")
    if isinstance(body, dict):
        raw = httpx.Response(status_code, json=body, request=request)
    else:
        raw = httpx.Response(status_code, text=body, request=request)
    return RequestFailed(Response(raw, object))
