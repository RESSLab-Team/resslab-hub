"""Alembic must work from any folder and with any password (#265). No database."""

import io
import logging

import pytest
from alembic.script import ScriptDirectory

import resslab_hub.utils.database as database
from alembic import command


@pytest.fixture
def elsewhere(tmp_path, monkeypatch):
    """Start from a folder with no alembic.ini in it."""
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def keep_logging():
    """env.py runs fileConfig, which replaces the root handlers (caplog's too)."""
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    yield
    root.handlers[:] = handlers
    root.setLevel(level)


def test_config_is_found_from_another_folder(elsewhere):
    script = ScriptDirectory.from_config(database.alembic_config())
    assert script.get_heads()


def test_offline_upgrade_with_escaped_password(elsewhere, keep_logging, monkeypatch):
    # quote_plus("p@ss%") is "p%40ss%25": a "%" that ConfigParser used to read
    # as an interpolation, so env.py raised before running any migration.
    monkeypatch.setattr(
        database, "url", "postgresql+psycopg://user:p%40ss%25@host:5432/db"
    )
    config = database.alembic_config()
    config.output_buffer = io.StringIO()

    command.upgrade(config, "heads", sql=True)

    assert "CREATE TABLE" in config.output_buffer.getvalue()
