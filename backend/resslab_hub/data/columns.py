"""The column list of every database, the same one a contributor sends.

The frontend test `fieldGroups.spec.ts` checks that every column has a
scientific category. It reads the list from `database-columns.json` at the
repo root, which this module writes (`make api`, also run by
`make generate-model`). `tests/test_database_columns.py` fails when the
committed file no longer matches the models.

    python -m resslab_hub.data.columns ../database-columns.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from resslab_hub.data.count_flags import COUNT_FLAGS
from resslab_hub.data.curation_status import STATUS_COLUMN
from resslab_hub.data.not_reported import NOT_REPORTED_COLUMN
from resslab_hub.models.database.brace import Brace
from resslab_hub.models.database.column import ColumnEntity
from resslab_hub.models.database.connection import Connection
from resslab_hub.models.database.ductile_fracture import DuctileFracture
from resslab_hub.models.database.eccentric_braced_frame import EccentricBracedFrame
from resslab_hub.models.database.hss_column import HSSColumn
from resslab_hub.models.database.material import Material
from resslab_hub.models.database.residual_stress import ResidualStress
from resslab_hub.models.database.tensile_coupon import TensileCoupon

# Frontend database id (DatabaseId in frontend/src/utils/navigation.ts) -> model.
# Same ids as README_DATABASES in uploader.py, same order as DatabaseId.
DATABASE_MODELS = {
    "connections": Connection,
    "columns": ColumnEntity,
    "braces": Brace,
    "hss": HSSColumn,
    "ebf": EccentricBracedFrame,
    "cyclic": Material,
    "tensile": TensileCoupon,
    "ductile-fracture": DuctileFracture,
    "residuals": ResidualStress,
}


def contributed_columns(model) -> list:
    """The model's columns minus the ones the Hub fills itself.

    The *_count flags are physical columns recomputed at upload; they have no
    CSV header in the data repo, and the validator treats them as unexpected.
    The review status is stamped by the submission (#253), so a contributor
    never sends it either. The `not_reported` list is written by the upload
    from the row's `nr` cells (#427).
    """
    derived = set(COUNT_FLAGS.get(model, {})) | {STATUS_COLUMN, NOT_REPORTED_COLUMN}
    return [c for c in model.__table__.c if c.key not in derived]


def database_columns() -> dict[str, list[str]]:
    """Column names per database, in dictionary order."""
    return {
        database: [c.key for c in contributed_columns(model)]
        for database, model in DATABASE_MODELS.items()
    }


def to_json() -> str:
    return json.dumps(database_columns(), indent=2) + "\n"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python -m resslab_hub.data.columns <output.json>")
    output = Path(sys.argv[1])
    output.write_text(to_json(), encoding="utf-8")
    print(f"write to {output.resolve()}")
