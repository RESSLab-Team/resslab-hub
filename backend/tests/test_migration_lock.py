"""Two backends that start together must not run the migrations twice (#479).

Each test runs "alembic upgrade head" in real processes, like two pods, on
its own empty database. The shared test database is built with create_all,
not Alembic, so it can't be used here.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

from resslab_hub.utils.database import MIGRATION_LOCK_ID, alembic_config
from tests.conftest import TEST_DB, _maintenance_url

BACKEND = Path(__file__).resolve().parents[1]
MIGRATE_DB = f"{TEST_DB}_migrate"


def _db_url(database: str) -> str:
    return _maintenance_url().rsplit("/", 1)[0] + f"/{database}"


@pytest.fixture
def empty_db():
    """A new empty database, dropped at the end."""
    admin = create_engine(_maintenance_url(), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{MIGRATE_DB}"'))
        conn.execute(text(f'CREATE DATABASE "{MIGRATE_DB}"'))
        conn.execute(text(f'REVOKE CONNECT ON DATABASE "{MIGRATE_DB}" FROM PUBLIC'))
    engine = create_engine(_db_url(MIGRATE_DB))
    yield engine
    engine.dispose()
    with admin.connect() as conn:
        conn.execute(
            text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = :db AND pid <> pg_backend_pid()"
            ),
            {"db": MIGRATE_DB},
        )
        conn.execute(text(f'DROP DATABASE IF EXISTS "{MIGRATE_DB}"'))
    admin.dispose()


def _start_upgrade() -> subprocess.Popen:
    env = {**os.environ, "POSTGRES_DB": MIGRATE_DB}
    return subprocess.Popen(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _finish(process: subprocess.Popen) -> str:
    output, _ = process.communicate(timeout=600)
    assert process.returncode == 0, output
    return output


def _versions(engine) -> list[str]:
    with engine.connect() as conn:
        return list(conn.scalars(text("SELECT version_num FROM alembic_version")))


def _head() -> str:
    return ScriptDirectory.from_config(alembic_config()).get_current_head()


def test_two_upgrades_at_the_same_time(empty_db):
    first, second = _start_upgrade(), _start_upgrade()
    outputs = [_finish(first), _finish(second)]

    assert _versions(empty_db) == [_head()]
    # The first migration (it creates the tables) ran in one process only.
    runs = sum(output.count("Running upgrade  ->") for output in outputs)
    assert runs == 1, outputs


def test_upgrade_waits_for_the_lock(empty_db):
    with empty_db.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text("SELECT pg_advisory_lock(:id)"), {"id": MIGRATION_LOCK_ID})
        process = _start_upgrade()
        time.sleep(3)
        assert process.poll() is None, "the upgrade did not wait for the lock"
        assert not inspect(empty_db).has_table("alembic_version")
        conn.execute(text("SELECT pg_advisory_unlock(:id)"), {"id": MIGRATION_LOCK_ID})

    output = _finish(process)
    assert "waiting for the lock" in output
    assert _versions(empty_db) == [_head()]
