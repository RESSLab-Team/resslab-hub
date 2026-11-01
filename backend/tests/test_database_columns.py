"""The committed database-columns.json must match the models.

The frontend test fieldGroups.spec.ts reads that file to check that every
column has a category. If the file is stale, the frontend test checks an old
schema and a new column without a category gets through.
"""

import json
from pathlib import Path

from resslab_hub.data.columns import database_columns
from resslab_hub.data.curation_status import STATUS_COLUMN

COLUMNS_FILE = Path(__file__).resolve().parents[2] / "database-columns.json"


def test_committed_file_matches_the_models():
    committed = json.loads(COLUMNS_FILE.read_text(encoding="utf-8"))
    assert committed == database_columns(), (
        "database-columns.json is stale: run `make api` and commit the file"
    )


def test_one_entry_per_frontend_database():
    assert list(database_columns()) == [
        "connections",
        "columns",
        "braces",
        "hss",
        "ebf",
        "cyclic",
        "tensile",
        "ductile-fracture",
        "residuals",
    ]


def test_leaves_out_the_columns_the_hub_fills():
    for database, columns in database_columns().items():
        assert STATUS_COLUMN not in columns, database
        assert not [name for name in columns if name.endswith("_count")], database
