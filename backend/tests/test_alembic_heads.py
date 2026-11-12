"""The migrations must end in one head.

Two branches that each add a migration on the same parent leave two heads.
Then "alembic upgrade head" fails and the backend does not start, and the
tests do not see it: they build the tables with create_all, not Alembic.
This test reads the scripts only, it needs no database.
"""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND = Path(__file__).resolve().parents[1]


def test_migrations_have_one_head():
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    heads = ScriptDirectory.from_config(config).get_heads()
    assert len(heads) == 1, (
        f"Alembic has {len(heads)} heads ({', '.join(heads)}): add a merge "
        "revision with `uv run alembic merge heads`"
    )
