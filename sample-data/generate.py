#!/usr/bin/env python3
"""Generate sample contribution records — a batch of experiments per database.

The values are invented, but their *types* are read from the SQLAlchemy models
and their *magnitudes* from the data already in the database, so a generated
batch exercises every branch of `POST /validate`: clean rows, rows with seeded
type errors, and rows whose values sit far enough outside the existing range to
raise the "please verify it" warning. Regenerate after a schema change with:

    make sample-data [EXPERIMENTS=15] [OUTLIERS=3]   # repo root or backend/

Run it through that target rather than directly: it points dynaconf at
`secrets/.env`, without which the database is unreachable and the generator
quietly falls back to type-based values with no range warnings at all.

Each database gets two files:
  <name>.csv         — N experiments, all type-valid; the last few carry
                       out-of-range values, so they validate with warnings
  <name>.invalid.csv — the same batch with type errors seeded into two rows

Both mirror the directory layout the backend expects inside an upload archive
(see `get_args_all` in backend/resslab_hub/data/uploader.py), so they can also be
tarred up and posted directly:

    tar czf braces.tar.gz braces/ && \
      curl -F file=@braces.tar.gz \
        "http://127.0.0.1:8000/validate?type=all-braces"
"""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from decimal import Decimal
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
    create_engine,
    func,
    select,
)
from sqlalchemy.orm import Session

from resslab_hub.data.validator import RANGE_MIN_COUNT
from resslab_hub.models.database.brace import Brace
from resslab_hub.models.database.column import ColumnEntity
from resslab_hub.models.database.connection import Connection
from resslab_hub.models.database.ductile_fracture import DuctileFracture
from resslab_hub.models.database.eccentric_braced_frame import EccentricBracedFrame
from resslab_hub.models.database.hss_column import HSSColumn
from resslab_hub.models.database.material import Material
from resslab_hub.models.database.residual_stress import ResidualStress
from resslab_hub.models.database.tensile_coupon import TensileCoupon
from resslab_hub.utils.database import url

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

OUTLIER_COLUMNS = 2  # columns blown out of range per outlier experiment


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


def range_stats(model, engine) -> dict[str, tuple[Decimal, Decimal]]:
    """Per-column (min, max) over existing data — the validator's own rule.

    Mirrors `TableValidator._range_stats`: only columns with at least
    RANGE_MIN_COUNT values are returned, because only those can raise a range
    warning. Returns {} when the database is unreachable, in which case the
    generator falls back to type-based values and seeds no warnings.
    """
    numeric_columns = [
        column
        for column in model.__table__.c
        if isinstance(column.type, (Integer, Numeric))
    ]
    if not numeric_columns:
        return {}
    aggregates = []
    for column in numeric_columns:
        aggregates.extend([func.count(column), func.min(column), func.max(column)])
    with Session(engine) as session:
        row = session.execute(select(*aggregates)).one()
    return {
        column.key: (Decimal(row[i * 3 + 1]), Decimal(row[i * 3 + 2]))
        for i, column in enumerate(numeric_columns)
        if row[i * 3] >= RANGE_MIN_COUNT and row[i * 3 + 1] is not None
    }


def plain(value: Decimal) -> str:
    """Format like the validator does when it quotes a range in a warning."""
    return format(value.normalize(), "f")


def as_text(column, value: Decimal) -> str:
    if kind(column) == "int":
        return str(int(value))
    return plain(value.quantize(Decimal("0.01")))


def in_range_value(column, bounds: tuple[Decimal, Decimal], index: int, count: int):
    """Spread the batch across the observed range, endpoints excluded."""
    low, high = bounds
    return as_text(column, low + (high - low) * Decimal(index) / Decimal(count + 1))


def out_of_range_value(column, bounds: tuple[Decimal, Decimal]) -> str:
    """One full span past the max is the warning threshold — go three."""
    low, high = bounds
    span = (high - low) or abs(high) or Decimal(1)
    return as_text(column, high + 3 * span)


def clean_value(column, prefix: str, index: int, count: int, stats: dict) -> str:
    key = column.key
    if key == "id":
        return f"DEMO-{prefix}-{index:03d}"
    category = kind(column)
    if category in ("int", "number") and key in stats:
        return in_range_value(column, stats[key], index, count)
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


def build_rows(model, prefix: str, count: int, stats: dict) -> list[dict[str, str]]:
    return [
        {c.key: clean_value(c, prefix, index, count, stats) for c in model.__table__.c}
        for index in range(1, count + 1)
    ]


def seed_outliers(
    model, rows: list[dict[str, str]], stats: dict, outliers: int
) -> list[str]:
    """Blow a couple of columns per outlier row past the warning threshold.

    Each outlier row targets different columns, so the batch shows the warning
    on several fields rather than the same one N times. Year columns are left
    alone: a date in the far future reads as a broken record, not an outlier.
    """
    targets = [
        c.key
        for c in model.__table__.c
        if c.key in stats and c.key != "date" and "year" not in c.key
    ]
    if not targets or not rows:
        return []

    notes: list[str] = []
    for offset, row in enumerate(rows[-outliers:] if outliers else []):
        chosen = [
            targets[(offset * OUTLIER_COLUMNS + i) % len(targets)]
            for i in range(min(OUTLIER_COLUMNS, len(targets)))
        ]
        for key in chosen:
            column = model.__table__.c[key]
            row[key] = out_of_range_value(column, stats[key])
            low, high = stats[key]
            notes.append(
                f"{row['id']}: {key}={row[key]} — outside {plain(low)} to {plain(high)}"
            )
    return notes


def seed_errors(model, rows: list[dict[str, str]]) -> tuple[list[dict], list[str]]:
    """Corrupt one column of each type, plus an NA in a non-nullable column.

    The errors go into two rows only, so the batch mixes passing and failing
    experiments the way a real multi-experiment submission would.
    """
    rows = [dict(row) for row in rows]
    error_rows = sorted({min(2, len(rows)), max(1, len(rows) // 2)})
    notes: list[str] = []

    for row_number in error_rows:
        row = rows[row_number - 1]
        used: set[str] = set()

        for category, (bad, why) in BAD_VALUES.items():
            for column in model.__table__.c:
                if column.key in used or column.key == "id":
                    continue
                if kind(column) == category:
                    row[column.key] = bad
                    used.add(column.key)
                    notes.append(f"{row['id']}: {column.key}={bad!r} — {why}")
                    break

        for column in model.__table__.c:
            if not column.nullable and column.key not in used and column.key != "id":
                row[column.key] = "NA"
                notes.append(
                    f"{row['id']}: {column.key}='NA' — null in a non-nullable column"
                )
                break

    return rows, notes


# --- Measured responses -----------------------------------------------------
#
# Not physics, but the right *character* per test: each kind gets its own curve
# shape and its own magnitudes, both taken from the corresponding directory in
# the data repo. That matters for the UI, whose sparkline plots column 1 against
# column 2 and normalises both axes — so specimens sharing a shape look
# identical no matter how the amplitudes differ.


@dataclass(frozen=True)
class Series:
    """One measured-response directory: where it goes and what it looks like."""

    directory: str
    columns: list[str]  # written in x, y order — the sparkline reads them that way
    shape: str
    x_peak: float
    y_peak: float
    rows: int = 240
    cycles: int = 6


def protocol(s: Series, scale: float, one_sided: bool = False) -> list[float]:
    """The imposed displacement history: two cycles at each growing amplitude.

    Real qualification protocols step the amplitude up and repeat each step,
    which is what gives measured data its nested-loop look.
    """
    steps = max(1, math.ceil(s.cycles / 2))
    history = []
    for i in range(s.rows):
        progress = i / (s.rows - 1) if s.rows > 1 else 0.0
        step = math.floor(s.cycles * progress / 2) + 1
        amplitude = s.x_peak * scale * min(1.0, step / steps)
        wave = math.sin(2 * math.pi * s.cycles * progress)
        history.append(
            amplitude * (0.5 - 0.5 * math.cos(math.pi * wave / 2 + math.pi))
            if one_sided
            else amplitude * wave
        )
    return history


def bilinear(
    s: Series,
    scale: float,
    yield_ratio: float = 0.2,
    hardening: float = 0.03,
    degrade: float = 0.0,
    pinch: float = 1.0,
    compression: float = 1.0,
) -> list[list[float]]:
    """Bilinear kinematic hardening — the standard idealisation of a steel test.

    Integrating the response over the displacement history (rather than writing
    y as a function of x) is what produces loops that enclose area: the
    unloading branch is elastic and steep, the reloading branch flat. The
    knobs are what make one test kind look unlike another:

    `degrade` fades the yield force cycle by cycle, `pinch` collapses the force
    near zero displacement (bolt slip, panel-zone shear), and `compression`
    caps the negative side lower than the positive one (brace buckling).
    """
    history = protocol(s, scale)
    peak = s.y_peak * scale
    stiffness = peak / (yield_ratio * s.x_peak * scale) if s.x_peak else peak

    out = []
    force = 0.0
    previous = history[0]
    for i, x in enumerate(history):
        progress = i / (len(history) - 1) if len(history) > 1 else 0.0
        strength = peak * (1 - degrade * progress)
        force += stiffness * (x - previous)
        # Kinematic hardening: the yield surface travels with the displacement.
        upper = hardening * stiffness * x + strength
        lower = hardening * stiffness * x - strength * compression
        force = min(max(force, lower), upper)
        previous = x

        reported = force
        if pinch < 1.0:
            span = abs(x) / (s.x_peak * scale) if s.x_peak else 1.0
            reported *= pinch + (1 - pinch) * min(1.0, span / 0.35)
        out.append([x, reported])
    return out


def ratchet(s: Series, scale: float) -> list[list[float]]:
    """Axial shortening: rotation cycles one-sided, shortening only accumulates."""
    out = []
    for i, x in enumerate(protocol(s, scale, one_sided=True)):
        progress = i / (s.rows - 1) if s.rows > 1 else 0.0
        # Shortening ratchets down a step with every excursion, never recovers.
        out.append([abs(x), -s.y_peak * scale * progress**1.6 * (0.9 + 0.1 * progress)])
    return out


def distribution(s: Series, scale: float, tilt: float = 0.0, flip: bool = False):
    """Residual stress across a section: self-equilibrating, so it sums to ~0.

    `3(2u-1)² - 1` has zero mean over the width by construction. The flange
    profiles are tension at the tips, the web profile is the other way round.
    """
    out = []
    for i in range(s.rows):
        u = i / (s.rows - 1)
        profile = 3 * (2 * u - 1) ** 2 - 1 + tilt * (2 * u - 1)
        y = s.y_peak * scale * profile * (-0.6 if flip else 1.0)
        out.append([s.x_peak * u, y])
    return out


def coefficients(s: Series, scale: float) -> list[list[float]]:
    """The quarter-point fit: a handful of numbers, one per column of the file."""
    return [[s.y_peak * scale * value] for value in (1.0, -0.55, 0.32, -0.18)[: s.rows]]


SHAPES = {
    # Stable plastic loops, mild strength loss: beams, strong-axis columns, HSS.
    "hysteresis": lambda s, scale: bilinear(s, scale, degrade=0.12),
    # Weak axis and the west-side connection: more cycles, visibly shrinking.
    "hysteresis_degrading": lambda s, scale: bilinear(s, scale, degrade=0.45),
    # Panel zone / bolt slip: the loop collapses to a waist through the origin.
    "pinched": lambda s, scale: bilinear(s, scale, pinch=0.22, degrade=0.1),
    # Brace: tension yields and hardens, compression buckles and keeps fading.
    "buckling": lambda s, scale: bilinear(
        s, scale, compression=0.4, degrade=0.3, hardening=0.06
    ),
    # Coupon: no degradation, strong hardening — loops grow instead of shrinking.
    "stress_strain": lambda s, scale: bilinear(
        s, scale, yield_ratio=0.3, hardening=0.12
    ),
    "ratchet": ratchet,
    "distribution_flange": distribution,
    "distribution_flange_tilted": lambda s, scale: distribution(s, scale, tilt=0.8),
    "distribution_web": lambda s, scale: distribution(s, scale, flip=True),
    "coefficients": coefficients,
}

ROTATION = ["Chord Rotation [rads]", "Moment [kN-mm]"]
DRIFT = ["Total story drift angle (rad)", "Force in the actuator (kN)"]
COORDINATE = ["coordinate", "residual_stress"]

# The filename is the foreign key, so each is written as <specimen id>.csv beside
# the record it belongs to. Peaks and row counts follow the real directories.
TIME_SERIES: dict[str, list[Series]] = {
    "braces": [
        Series(
            "braces/force_displacement",
            ["Displacement [mm]", "Force [kN]"],
            "buckling",
            x_peak=40,
            y_peak=800,
            rows=300,
            cycles=9,
        )
    ],
    "columns": [
        Series(
            "columns/axial_shortening_rotation",
            ["Chord Rotation [rads]", "Axial Shortening [mm]"],
            "ratchet",
            x_peak=0.13,
            y_peak=18,
            rows=600,
            cycles=13,
        ),
        Series(
            "columns/moment_rotation_strong",
            ROTATION,
            "hysteresis",
            x_peak=0.017,
            y_peak=80000,
            rows=300,
            cycles=9,
        ),
        Series(
            "columns/moment_rotation_weak",
            ROTATION,
            "hysteresis_degrading",
            x_peak=0.088,
            y_peak=32000,
            rows=370,
            cycles=15,
        ),
    ],
    "connections": [
        Series(
            "connections/Beam_moment_rotation",
            ROTATION,
            "hysteresis",
            x_peak=0.06,
            y_peak=2400000,
            rows=460,
            cycles=16,
        ),
        Series(
            "connections/Beam_moment_rotation_west",
            ROTATION,
            "hysteresis_degrading",
            x_peak=0.06,
            y_peak=2300000,
            rows=460,
            cycles=16,
        ),
        Series(
            "connections/Global",
            DRIFT,
            "hysteresis",
            x_peak=0.05,
            y_peak=1100,
            rows=380,
            cycles=10,
        ),
        Series(
            "connections/Global_west",
            DRIFT,
            "hysteresis",
            x_peak=0.05,
            y_peak=1050,
            rows=380,
            cycles=10,
        ),
        Series(
            "connections/Panel_zone",
            ["panel zone shear distortion (rad)", "panel zone shear force (kN)"],
            "pinched",
            x_peak=0.009,
            y_peak=3000,
            rows=600,
            cycles=15,
        ),
    ],
    "hss_columns": [
        Series(
            "hss_columns/Moment_Rotation",
            ["rotation (rad)", "moment (kN.m)"],
            "hysteresis",
            x_peak=0.055,
            y_peak=200,
            rows=140,
            cycles=6,
        )
    ],
    "cyclic_coupons": [
        Series(
            "material/cyclic_coupons/stress_strain",
            ["e_true", "Sigma_true"],
            "stress_strain",
            x_peak=0.02,
            y_peak=370,
            rows=200,
            cycles=7,
        )
    ],
    "residual_stresses": [
        Series(
            "residual_stresses/Distributions/Distributions_F1",
            COORDINATE,
            "distribution_flange",
            x_peak=297,
            y_peak=35,
            rows=13,
        ),
        Series(
            "residual_stresses/Distributions/Distributions_F2",
            COORDINATE,
            "distribution_flange_tilted",
            x_peak=297,
            y_peak=32,
            rows=13,
        ),
        Series(
            "residual_stresses/Distributions/Distributions_W1",
            COORDINATE,
            "distribution_web",
            x_peak=210,
            y_peak=45,
            rows=13,
        ),
        Series(
            "residual_stresses/QP_Coefficients",
            ["qp_coefficient"],
            "coefficients",
            x_peak=0,
            y_peak=80,
            rows=4,
        ),
    ],
}


def series_rows(series: Series, scale: float) -> list[list[str]]:
    values = SHAPES[series.shape](series, scale)
    return [[f"{value:.6f}" for value in row[: len(series.columns)]] for row in values]


def write_series(path: Path, series: Series, scale: float) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = series_rows(series, scale)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(series.columns)
        writer.writerows(rows)
    return len(rows)


def write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--experiments",
        type=int,
        default=15,
        help="experiments per database (default: 15)",
    )
    parser.add_argument(
        "--outliers",
        type=int,
        default=3,
        help="of those, how many carry out-of-range values (default: 3)",
    )
    args = parser.parse_args()
    count = max(1, args.experiments)
    outliers = max(0, min(args.outliers, count))

    root = Path(__file__).resolve().parent
    engine = create_engine(url, echo=False)
    summary: list[str] = []

    for name, (model, csv_path, prefix) in DATABASES.items():
        columns = [c.key for c in model.__table__.c]
        try:
            stats = range_stats(model, engine)
        except Exception as exc:  # no database: fall back to type-based values
            stats = {}
            summary.append(f"{name}: no range data ({type(exc).__name__}) — see below")

        rows = build_rows(model, prefix, count, stats)
        outlier_notes = seed_outliers(model, rows, stats, outliers)
        bad_rows, error_notes = seed_errors(model, rows)

        stem = Path(csv_path)
        write_csv(root / stem, columns, rows)
        write_csv(root / stem.with_suffix(".invalid.csv"), columns, bad_rows)

        summary.append(
            f"{name}: {count} experiments × {len(columns)} columns -> {stem}"
            f"  [{rows[0]['id']} … {rows[-1]['id']}]"
        )
        summary.append(
            f"    in range: {len(stats)} columns have ≥ {RANGE_MIN_COUNT} values "
            f"in the database, so their values are drawn from it"
        )
        for note in outlier_notes:
            summary.append(f"    warning: {note}")
        if stats and not outlier_notes:
            summary.append("    warning: none seeded (--outliers 0)")
        if not stats:
            summary.append(
                "    warning: none possible — no column has enough data yet "
                "(run `make upload-data`)"
            )
        for note in error_notes:
            summary.append(f"    invalid: {note}")

        # Measured response, named after each record's id so the validator's
        # foreign-key check resolves against the primary CSV in the same archive.
        for series in TIME_SERIES.get(name, []):
            written = 0
            for index, row in enumerate(rows, 1):
                series_path = Path(series.directory) / f"{row['id']}.csv"
                # Vary the amplitude per specimen; the shape is what the kind is.
                written = write_series(
                    root / series_path, series, scale=0.7 + index / 20
                )
            summary.append(
                f"    series: {series.directory}/{{{rows[0]['id']} … "
                f"{rows[-1]['id']}}}.csv ({count} files, {written} rows, "
                f"{series.shape})"
            )

    print("\n".join(summary))


if __name__ == "__main__":
    main()
