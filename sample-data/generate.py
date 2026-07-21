#!/usr/bin/env python3
"""Generate sample contribution records, one CSV per database.

The values are invented, but their *types* are read straight from the SQLAlchemy
models, so a clean record passes `POST /validate` and a flawed one fails with
predictable, per-field errors. Regenerate after a schema change with:

    cd backend && uv run python ../sample-data/generate.py

Each database gets two files:
  <name>.csv         — every column populated with a valid value
  <name>.invalid.csv — the same record with seeded type errors

Both mirror the directory layout the backend expects inside an upload archive
(see `get_args_all` in backend/resslab_hub/data/uploader.py), so they can also be
tarred up and posted directly:

    tar czf braces.tar.gz braces/ && \
      curl -u user:$API_PASSWORD -F file=@braces.tar.gz \
        "http://127.0.0.1:8000/validate?type=all-braces"
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    Float,
    Integer,
    Numeric,
    SmallInteger,
    String,
)

from resslab_hub.models.database.brace import Brace
from resslab_hub.models.database.column import ColumnEntity
from resslab_hub.models.database.connection import Connection
from resslab_hub.models.database.ductile_fracture import DuctileFracture
from resslab_hub.models.database.eccentric_braced_frame import EccentricBracedFrame
from resslab_hub.models.database.hss_column import HSSColumn
from resslab_hub.models.database.material import Material
from resslab_hub.models.database.residual_stress import ResidualStress
from resslab_hub.models.database.tensile_coupon import TensileCoupon

# database key -> (model, path of the primary CSV inside an upload archive, id prefix)
DATABASES = {
    "braces": (Brace, "braces/steel_braces.csv", "BRC"),
    "columns": (ColumnEntity, "columns/steel_columns.csv", "COL"),
    "connections": (Connection, "connections/connections.csv", "CON"),
    "hss_columns": (HSSColumn, "hss_columns/hss_columns.csv", "HSS"),
    "cyclic_coupons": (Material, "material/cyclic_coupons/steel_material.csv", "MAT"),
    "tensile_coupons": (
        TensileCoupon,
        "material/tensile_coupons/tensile_coupons.csv",
        "TC",
    ),
    "ductile_fracture": (
        DuctileFracture,
        "material/ductile_fracture/ductile_fracture.csv",
        "DF",
    ),
    "residual_stresses": (
        ResidualStress,
        "residual_stresses/residual_stresses.csv",
        "RS",
    ),
    "eccentric_braced_frames": (
        EccentricBracedFrame,
        "eccentric_braced_frames/eccentric_braced_frames.csv",
        "EBF",
    ),
}

# Substring -> value. Checked in order, so put the specific patterns first;
# anything unmatched falls back to the column's type.
STRING_HINTS: list[tuple[tuple[str, ...], str]] = [
    (("investigator", "author"), "Demo Investigator et al."),
    (("experimental_program", "program"), "DEMO Sample Program 2025"),
    (("specimen_designation", "specimen_id", "specimen_type"), "DEMO-SPEC-01"),
    (("reference", "citation"), "Demo et al. (2025), J. Struct. Eng."),
    (("link", "url", "doi"), "https://example.org/demo-dataset"),
    (("cross_section_shape", "section_type", "profile_type"), "Wide Flange"),
    (("cross_section_size", "section", "profile", "tube_section"), "W14x176"),
    (("steel", "grade", "material", "spec"), "ASTM A992"),
    (("loading_protocol", "loading", "protocol"), "Symmetric Cyclic"),
    (("boundary_condition", "configuration", "confi"), "Fixed-Fixed"),
    (("weld", "bolt"), "Fillet"),
    (("direction", "orientation", "angle"), "Strong Axis"),
    (("location", "source"), "Flange"),
    (("standard",), "ASTM E8"),
    (("class",), "Compact"),
    (("comment", "note", "description"), "Synthetic record for UI testing."),
]

# Seeded failures for the .invalid.csv variant, by column type. Each entry is a
# (bad value, why it fails) pair the backend validator will reject.
# Note the integer case is a non-numeric string rather than something like
# "12.75": the validator parses integers as `int(Decimal(value))`, which happily
# truncates a decimal, so a fractional value would not actually be rejected.
BAD_VALUES = {
    "number": ("not-a-number", "non-numeric value in a numeric column"),
    "int": ("not-an-integer", "non-numeric value in an integer column"),
    "bool": ("maybe", "value outside yes/no in a boolean column"),
    "date": ("2025-13-45", "date outside the DD.MM.YY / DD.MM.YYYY formats"),
}


def string_value(key: str) -> str:
    lowered = key.lower()
    for needles, value in STRING_HINTS:
        if any(needle in lowered for needle in needles):
            return value
    return "Demo value"


def kind(column) -> str:
    """Collapse the SQLAlchemy type to the categories the validator checks."""
    t = column.type
    if isinstance(t, String):
        return "string"
    if isinstance(t, Boolean):
        return "bool"
    if isinstance(t, (SmallInteger, Integer, BigInteger)):
        return "int"
    if isinstance(t, Date):
        return "date"
    if isinstance(t, (Float, Numeric)):
        return "number"
    return "string"


def clean_value(column, key: str, prefix: str, index: int) -> str:
    if key == "id":
        return f"DEMO-{prefix}-{index:03d}"
    category = kind(column)
    if category == "string":
        return string_value(key)
    if category == "bool":
        return "yes"
    if category == "date":
        return "15.03.25"
    if category == "int":
        # `date` is a plain year on several tables.
        return "2025" if "year" in key.lower() or key == "date" else "4"
    return "123.45"


def build_row(model, prefix: str, index: int) -> dict[str, str]:
    return {
        c.key: clean_value(c, c.key, prefix, index) for c in model.__table__.c
    }


def seed_errors(model, row: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    """Corrupt one column of each type, plus an NA in a non-nullable column."""
    row = dict(row)
    notes: list[str] = []
    used: set[str] = set()

    for category, (bad, why) in BAD_VALUES.items():
        for column in model.__table__.c:
            if column.key in used or column.key == "id":
                continue
            if kind(column) == category:
                row[column.key] = bad
                used.add(column.key)
                notes.append(f"{column.key}={bad!r} — {why}")
                break

    for column in model.__table__.c:
        if not column.nullable and column.key not in used and column.key != "id":
            row[column.key] = "NA"
            used.add(column.key)
            notes.append(f"{column.key}='NA' — null in a non-nullable column")
            break

    return row, notes


# Measured-response files, mirroring the subsidiary types `get_args_all` expands
# an `all-*` upload into. The filename is the foreign key, so each is written as
# <specimen id>.csv beside the record it belongs to.
#   database key -> [(directory, required columns)]
TIME_SERIES: dict[str, list[tuple[str, list[str]]]] = {
    "braces": [("braces/force_displacement", ["Displacement [mm]", "Force [kN]"])],
    "columns": [
        (
            "columns/axial_shortening_rotation",
            ["Chord Rotation [rads]", "Axial Shortening [mm]"],
        ),
        ("columns/moment_rotation_strong", ["Chord Rotation [rads]", "Moment [kN-mm]"]),
        ("columns/moment_rotation_weak", ["Chord Rotation [rads]", "Moment [kN-mm]"]),
    ],
    "connections": [
        (
            "connections/Beam_moment_rotation",
            ["Chord Rotation [rads]", "Moment [kN-mm]"],
        ),
        (
            "connections/Beam_moment_rotation_west",
            ["Chord Rotation [rads]", "Moment [kN-mm]"],
        ),
        (
            "connections/Global",
            ["Total story drift angle (rad)", "Force in the actuator (kN)"],
        ),
        (
            "connections/Global_west",
            ["Total story drift angle (rad)", "Force in the actuator (kN)"],
        ),
        (
            "connections/Panel_zone",
            ["panel zone shear distortion (rad)", "panel zone shear force (kN)"],
        ),
    ],
    "hss_columns": [
        ("hss_columns/Moment_Rotation", ["rotation (rad)", "moment (kN.m)"])
    ],
    "cyclic_coupons": [
        ("material/cyclic_coupons/stress_strain", ["Sigma_true", "e_true"])
    ],
    "residual_stresses": [
        (
            "residual_stresses/Distributions/Distributions_F1",
            ["coordinate", "residual_stress"],
        ),
        (
            "residual_stresses/Distributions/Distributions_F2",
            ["coordinate", "residual_stress"],
        ),
        (
            "residual_stresses/Distributions/Distributions_W1",
            ["coordinate", "residual_stress"],
        ),
        ("residual_stresses/QP_Coefficients", ["qp_coefficient"]),
    ],
}


def series_rows(columns: list[str], count: int = 60) -> list[list[str]]:
    """An open hysteresis loop — the right *shape* for a cyclic test, not physics.

    The response lags the driver, so plotting column 2 against column 1 gives a
    loop rather than a straight line, and the amplitude grows as a stepped
    cyclic protocol would.
    """
    rows = []
    for i in range(count):
        phase = 2 * math.pi * 3 * i / count
        growth = 1 + 2 * i / count
        driver = 0.01 * growth * math.sin(phase)
        response = 900 * growth * math.sin(phase - 0.4) / (1 + 0.4 * i / count)
        values = [driver, response]
        rows.append([f"{v:.6f}" for v in values[: len(columns)]])
    return rows


def write_series(path: Path, columns: list[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = series_rows(columns)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        writer.writerows(rows)
    return len(rows)


def write_csv(path: Path, columns: list[str], row: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerow(row)


def main() -> None:
    root = Path(__file__).resolve().parent
    summary: list[str] = []

    for index, (name, (model, csv_path, prefix)) in enumerate(DATABASES.items(), 1):
        columns = [c.key for c in model.__table__.c]
        row = build_row(model, prefix, index)
        bad_row, notes = seed_errors(model, row)

        stem = Path(csv_path)
        write_csv(root / stem, columns, row)
        write_csv(
            root / stem.with_suffix(".invalid.csv"),
            columns,
            bad_row,
        )

        summary.append(f"{name} ({len(columns)} columns) -> {stem}")
        for note in notes:
            summary.append(f"    invalid: {note}")

        # Measured response, named after the record's id so the validator's
        # foreign-key check resolves against the primary CSV in the same archive.
        specimen = row["id"]
        for directory, series_columns in TIME_SERIES.get(name, []):
            series_path = Path(directory) / f"{specimen}.csv"
            count = write_series(root / series_path, series_columns)
            summary.append(f"    series: {series_path} ({count} rows)")

    print("\n".join(summary))


if __name__ == "__main__":
    main()
