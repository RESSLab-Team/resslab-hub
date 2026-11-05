#!/usr/bin/env python3
"""Generate sample contribution batches, one per database.

Each row starts from a real record of the database (its "template"). The
numbers move by a few percent, and the fields that say who did the test (id,
investigator, reference, link...) are replaced by demo values. The curves are
the template's real curves from the data repo, downsampled. So a batch looks
like real data, and it goes through every check of `POST /validate`.

    make sample-data [EXPERIMENTS=15] [OUTLIERS=3]   # repo root or backend/

Run it through that target rather than directly: it points dynaconf at
`secrets/.env` (without it the database is unreachable) and passes the data
repo with `--data-dir`. Without the database, the values fall back to one fixed
value per column type, with no range warnings. Without the data repo, the
curves fall back to synthetic shapes.

Each database gets two files:
  <name>.csv          N experiments, all valid. The last few carry values far
                      outside the existing range, so they validate with warnings
  <name>.invalid.csv  the same batch with one seeded problem per row, one for
                      each check of the validator (see README.md)

At the end the real validator runs on both, the way a submission does, and the
script prints `ok` or the differences for each database (`--no-check` skips it).

Both mirror the directory layout the backend expects inside an upload archive
(see `get_args_all` in backend/resslab_hub/data/uploader.py), so they can also be
tarred up and posted directly:

    tar czf braces.tar.gz braces/ && \
      curl -F file=@braces.tar.gz -u user:$API_PASSWORD \
        "http://127.0.0.1:8000/validate?type=all-braces"
"""

from __future__ import annotations

import argparse
import csv
import io
import logging
import math
import random
import shutil
import tempfile
from dataclasses import dataclass, field, replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Callable, Optional

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

from resslab_hub.data.columns import contributed_columns
from resslab_hub.data.common import SAFE_ID_PATTERN
from resslab_hub.data.uploader import Type
from resslab_hub.data.validator import (
    MISSING_MARKERS,
    RANGE_MIN_COUNT,
    DuctileFractureTableValidator,
    parse_number,
    validate_all,
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
from resslab_hub.utils.database import url


@dataclass(frozen=True)
class Database:
    model: type
    csv_path: str  # the primary CSV inside an upload archive
    prefix: str  # of the demo ids
    input_type: Type  # what /validate is called with


DATABASES = {
    "braces": Database(Brace, "braces/steel_braces.csv", "BRC", Type.ALL_BRACE),
    "columns": Database(
        ColumnEntity, "columns/steel_columns.csv", "COL", Type.ALL_COLUMN
    ),
    "connections": Database(
        Connection, "connections/connections.csv", "CON", Type.ALL_CONNECTION
    ),
    "hss_columns": Database(
        HSSColumn, "hss_columns/hss_columns.csv", "HSS", Type.ALL_HSS_COLUMN
    ),
    "cyclic_coupons": Database(
        Material,
        "material/cyclic_coupons/steel_material.csv",
        "MAT",
        Type.ALL_MATERIAL,
    ),
    "tensile_coupons": Database(
        TensileCoupon,
        "material/tensile_coupons/tensile_coupons.csv",
        "TC",
        Type.ALL_TENSILE_COUPON,
    ),
    "ductile_fracture": Database(
        DuctileFracture,
        "material/ductile_fracture/ductile_fracture.csv",
        "DF",
        Type.ALL_DUCTILE_FRACTURE,
    ),
    "residual_stresses": Database(
        ResidualStress,
        "residual_stresses/residual_stresses.csv",
        "RS",
        Type.ALL_RESIDUAL_STRESS,
    ),
    "eccentric_braced_frames": Database(
        EccentricBracedFrame,
        "eccentric_braced_frames/eccentric_braced_frames.csv",
        "EBF",
        Type.ALL_ECCENTRIC_BRACED_FRAME,
    ),
}

# The fields that say who did the test and where it is published. They are
# replaced in every row, so a sample batch never passes for someone's record.
IDENTITY = {
    "investigator": "Demo Investigator et al.",
    "experimental_program": "DEMO Sample Program 2025",
    "reference": "Demo et al. (2025), J. Struct. Eng.",
    "link": "https://example.org/demo-dataset",
    "url": "https://example.org/demo-dataset",
}
SPECIMEN_NAMES = ("specimen_designation", "specimen_ID", "spec_id")

# Only for the fallback without a database: substring -> value, checked in
# order, so put the specific patterns first. Unmatched columns get "Demo value".
STRING_HINTS: list[tuple[tuple[str, ...], str]] = [
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

JITTER = (0.94, 1.06)  # one factor per row, shared by its numbers and curves
NOISE = (0.99, 1.01)  # per column, on top of the row factor
JITTER_MIN_DISTINCT = 5  # fewer values than that is a setting, not a measure
NO_JITTER = {"latitude", "longitude"}
OUTLIER_COLUMNS = 2  # columns pushed out of range per outlier experiment
UNIT_SLIP = Decimal(1000)  # kN written as N, m as mm...

# Columns with a rule of their own in the validator: the generic seeds leave
# them alone, so each seed raises only the message it is about.
RULE_COLUMNS = {"flange_nr_data", "has_sem"}
DF_LIST_COLUMNS = ("loading_protocol",)  # plus every meas_* column
# A cell written as 3,5 without quotes. csv.writer would quote it, so the row is
# written with this token and the token is replaced in the text afterwards.
COMMA_TOKEN = "@@DECIMAL_COMMA@@"
# The uploader stores NA, NR and NaN in a text column as these words. A
# contributor writes the marker, so the templates write it back.
STORED_MARKERS = {
    "Not applicable": "NA",
    "Not reported": "NR",
    "Not a number": "NA",
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


def yearish(key: str) -> bool:
    return key == "date" or "year" in key.lower()


def bookkeeping(key: str) -> bool:
    """An internal index (cyclic coupons): no contributor reads it as a measure."""
    return key.startswith("hidden_")


def is_list_column(key: str) -> bool:
    return key in DF_LIST_COLUMNS or key.startswith("meas_")


def is_number_list(text: str) -> bool:
    return DuctileFractureTableValidator._is_number_list(text)


def plain(value: Decimal) -> str:
    """Format like the validator does when it quotes a range in a warning."""
    return format(value.normalize(), "f")


def number(text: str) -> Optional[Decimal]:
    """The cell as a number, or None when the validator would not read one."""
    value, message = parse_number(text)
    return None if message else value


def range_stats(model, engine) -> dict[str, tuple[Decimal, Decimal]]:
    """Per-column (min, max) over existing data, the validator's own rule.

    Mirrors `TableValidator._range_stats`: only columns with at least
    RANGE_MIN_COUNT values are returned, because only those can raise a range
    warning. The bounds go through `str()` like in the validator, so a float
    0.1 stays 0.1 and not its long binary expansion.
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
    stats = {}
    for i, column in enumerate(numeric_columns):
        count, low, high = row[i * 3], row[i * 3 + 1], row[i * 3 + 2]
        if count < RANGE_MIN_COUNT or low is None:
            continue
        low, high = Decimal(str(low)), Decimal(str(high))
        if low.is_finite() and high.is_finite():
            stats[column.key] = (low, high)
    return stats


# --- Rows from real templates ----------------------------------------------


@dataclass
class Record:
    """One row of the batch, and where it comes from."""

    values: dict[str, str]  # the CSV row, as written
    factor: float  # the row's scale, shared with its curves
    source_id: Optional[str] = None  # the template's id, None for the fallback


def load_rows(model, engine) -> list[dict]:
    columns = contributed_columns(model)
    with Session(engine) as session:
        result = session.execute(select(*columns)).all()
    rows = [dict(zip((c.key for c in columns), values)) for values in result]
    return sorted(rows, key=lambda row: str(row["id"]))


def is_missing(value) -> bool:
    """True when the cell would hold no value once written."""
    if value is None:
        return True
    if isinstance(value, float):
        return not math.isfinite(value)
    if isinstance(value, Decimal):
        return not value.is_finite()
    if isinstance(value, str):
        return value in STORED_MARKERS or value.strip().upper() in (
            "",
            *MISSING_MARKERS,
        )
    return False


def usable(model, row: dict) -> bool:
    """A template must make a clean row: no hole in a mandatory column, and
    nothing that one of the table's own rules warns about."""
    for column in contributed_columns(model):
        value = row[column.key]
        if not column.nullable and is_missing(value):
            return False
        if model is DuctileFracture and is_list_column(column.key):
            if not is_missing(value) and not is_number_list(str(value).strip()):
                return False
    if model is ResidualStress and row.get("flange_nr_data") not in (1, 2):
        return False
    return True


def cell_text(value) -> str:
    """The value as a contributor writes it in the CSV."""
    if isinstance(value, str) and value in STORED_MARKERS:
        return STORED_MARKERS[value]
    if is_missing(value):
        return "NA"  # only reached for nullable columns, cf. `usable`
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, date):
        return value.strftime("%d.%m.%Y")
    if isinstance(value, Decimal):
        return plain(value)
    if isinstance(value, float):
        return plain(Decimal(repr(value)))
    if isinstance(value, int):
        return str(value)
    # A CR inside a quoted cell still reads as Windows line endings.
    return str(value).replace("\r\n", "\n").replace("\r", "\n")


def jittered(
    text: str,
    factor: float,
    rng: random.Random,
    bounds: Optional[tuple[Decimal, Decimal]],
) -> str:
    """Scale by the row factor and a little noise, with the source's decimals.

    A value that would leave the existing range keeps the template's value: an
    in-range warning on a clean row would be noise.
    """
    value = Decimal(text)
    scale = Decimal(str(round(factor * rng.uniform(*NOISE), 6)))
    places = min(6, max(0, -value.as_tuple().exponent))
    moved = (value * scale).quantize(Decimal(1).scaleb(-places))
    if moved == 0:
        moved = abs(moved)  # no "-0"
    if bounds and not bounds[0] <= moved <= bounds[1]:
        return text
    return plain(moved)


def demo_identity(values: dict[str, str], db: Database, index: int, ebf_base: int):
    if db.model is EccentricBracedFrame:
        values["id"] = str(ebf_base + index)  # EBF ids are whole numbers
    else:
        values["id"] = f"DEMO-{db.prefix}-{index:03d}"
    for key, text in IDENTITY.items():
        if key in values:
            values[key] = text
    for key in SPECIMEN_NAMES:
        if key in values:
            values[key] = f"DEMO-SPEC-{index:02d}"
    if "has_sem" in values:
        values["has_sem"] = "NR"  # the hub sets it when it processes the images


def pick_templates(
    templates: list[dict], count: int, rng: random.Random, score: Callable
) -> list[dict]:
    """Round-robin over the programs, so one batch shows several of them.

    Within a program, the records with the most curve files come first. When
    the table has fewer usable records than asked, they are used again.
    """
    groups: dict[str, list[dict]] = {}
    for row in templates:
        key = row.get("reference") or row.get("investigator") or ""
        groups.setdefault(str(key), []).append(row)
    queues = []
    for key in sorted(groups):
        members = groups[key][:]
        rng.shuffle(members)
        members.sort(key=score, reverse=True)  # stable: shuffled within a score
        queues.append(members)
    rng.shuffle(queues)
    order = [
        queue[depth]
        for depth in range(max(len(queue) for queue in queues))
        for queue in queues
        if depth < len(queue)
    ]
    return [order[i % len(order)] for i in range(count)]


def from_templates(
    db: Database,
    templates: list[dict],
    all_rows: list[dict],
    count: int,
    stats: dict,
    rng: random.Random,
    curves: CurveSource,
    ebf_base: int,
) -> list[Record]:
    columns = contributed_columns(db.model)
    distinct = {
        c.key: len({row[c.key] for row in all_rows if row[c.key] is not None})
        for c in columns
    }
    picks = pick_templates(templates, count, rng, lambda row: curves.score(db, row))
    records = []
    for index, template in enumerate(picks, 1):
        factor = rng.uniform(*JITTER)
        values = {}
        for column in columns:
            text = cell_text(template[column.key])
            if (
                kind(column) == "number"
                and column.key not in NO_JITTER
                and distinct[column.key] >= JITTER_MIN_DISTINCT
                and number(text) is not None
            ):
                text = jittered(text, factor, rng, stats.get(column.key))
            values[column.key] = text
        demo_identity(values, db, index, ebf_base)
        records.append(Record(values, factor, str(template["id"])))
    return records


def fallback_text(model, column, index: int, count: int, stats: dict) -> str:
    """A value from the column type alone, for a table with no usable rows."""
    key = column.key
    category = kind(column)
    if category in ("int", "number") and key in stats:
        low, high = stats[key]
        value = low + (high - low) * Decimal(index) / Decimal(count + 1)
        if category == "int":
            return str(int(value))
        return plain(value.quantize(Decimal("1e-6")))
    if category == "string":
        if model is DuctileFracture and is_list_column(key):
            return "[7.99, 7.99, 8.01]"
        if key == "date":
            return "15.03.2025"
        return string_value(key)
    if category == "bool":
        return "yes"
    if category == "date":
        return "15.03.2025"
    if category == "int":
        if yearish(key):
            return "2025"
        return "1" if key == "flange_nr_data" else "4"
    return "123.45"


def from_types(
    db: Database, count: int, stats: dict, rng: random.Random, ebf_base: int
) -> list[Record]:
    records = []
    for index in range(1, count + 1):
        values = {
            c.key: fallback_text(db.model, c, index, count, stats)
            for c in contributed_columns(db.model)
        }
        demo_identity(values, db, index, ebf_base)
        records.append(Record(values, rng.uniform(*JITTER)))
    return records


# --- Expected validator messages ---------------------------------------------


@dataclass(frozen=True)
class Expect:
    """One message the validator must give, and only it."""

    row: int
    column: str
    level: str  # "error" or "warning"
    message: str  # a part of the validator's message


RANGE_MESSAGE = "Far outside the existing range"


# --- Range warnings -----------------------------------------------------------


def seed_outliers(
    model, records: list[Record], stats: dict, outliers: int
) -> tuple[list[Expect], list[str]]:
    """Push a couple of columns per outlier row past the warning threshold.

    The value looks like a real mistake: the template's value times 1000 (a
    unit slip) when that is far enough, else three spans above the maximum.
    Each outlier row takes other columns, so the batch shows the warning on
    several fields. Years, coordinates, internal indexes and columns with
    their own rule are left alone: a date in the far future reads as a broken
    record, not as a value to check.
    """
    targets = [
        c.key
        for c in contributed_columns(model)
        if c.key in stats
        and kind(c) in ("int", "number")
        and c.key != "id"
        and not yearish(c.key)
        and not bookkeeping(c.key)
        and c.key not in NO_JITTER
        and c.key not in RULE_COLUMNS
    ]
    if not targets or not records or not outliers:
        return [], []

    expects, notes = [], []
    first = len(records) - outliers + 1
    for offset, record in enumerate(records[-outliers:]):
        row = first + offset
        chosen = [
            targets[(offset * OUTLIER_COLUMNS + i) % len(targets)]
            for i in range(min(OUTLIER_COLUMNS, len(targets)))
        ]
        for key in chosen:
            low, high = stats[key]
            span = (high - low) or abs(high) or Decimal(1)
            current = number(record.values[key])
            if current is not None and not (
                low - span <= current * UNIT_SLIP <= high + span
            ):
                value, why = current * UNIT_SLIP, "unit slip x1000"
            else:
                value, why = high + 3 * span, "three spans above the max"
            if kind(model.__table__.c[key]) == "int":
                value = value.to_integral_value()
            record.values[key] = plain(value)
            expects.append(Expect(row, key, "warning", RANGE_MESSAGE))
            notes.append(
                f"row {row}: {key}={record.values[key]} ({why}, "
                f"range {plain(low)} to {plain(high)})"
            )
    return expects, notes


# --- The .invalid.csv: one problem per row -----------------------------------


@dataclass
class Seeded:
    note: str
    expects: list[Expect]


@dataclass
class Invalid:
    """The invalid batch while its seeds are placed."""

    db: Database
    rows: list[dict[str, str]]
    records: list[Record]
    used: list[set[str]]  # per row, the cells a seed (or an outlier) owns
    comma_row: Optional[int] = None

    @property
    def model(self):
        return self.db.model

    @property
    def is_ebf(self) -> bool:
        return self.model is EccentricBracedFrame

    def cell(self, r: int, key: str) -> str:
        return self.rows[r - 1][key]

    def set(self, r: int, key: str, value: str):
        self.rows[r - 1][key] = value
        self.used[r - 1].add(key)

    def free(self, r: int, *tests: Callable) -> Optional[object]:
        """The first column that passes the first test that finds one.

        The internal indexes come last: a seed there teaches nothing.
        """
        columns = sorted(
            contributed_columns(self.model), key=lambda c: bookkeeping(c.key)
        )
        for test in tests:
            for column in columns:
                if column.key == "id" or column.key in self.used[r - 1]:
                    continue
                if test(column):
                    return column
        return None


def whole(text: str) -> Optional[int]:
    value = number(text)
    if value is None or value != value.to_integral_value():
        return None
    return int(value)


def seed_comma(b: Invalid, r: int) -> Optional[Seeded]:
    column = b.free(r, lambda c: kind(c) == "number")
    if column is None:
        return None
    b.set(r, column.key, COMMA_TOKEN)
    # The validator skips the rest of the row: nothing else can go on it.
    b.used[r - 1].update(c.key for c in contributed_columns(b.model))
    b.comma_row = r
    return Seeded(
        f"{column.key}=3,5 without quotes, so the row has one value too many",
        [Expect(r, "row", "error", "A decimal comma splits a row")],
    )


def seed_text_in_number(b: Invalid, r: int) -> Optional[Seeded]:
    column = b.free(r, lambda c: kind(c) == "number")
    if column is None:
        return None
    b.set(r, column.key, "N/A")
    return Seeded(
        f"{column.key}='N/A', text in a number column",
        [Expect(r, column.key, "error", "Must be a number.")],
    )


def int_column(b: Invalid, r: int):
    def plain_int(c):
        return kind(c) == "int" and c.key not in RULE_COLUMNS

    return b.free(
        r,
        lambda c: (
            plain_int(c)
            and not yearish(c.key)
            and not bookkeeping(c.key)
            and whole(b.cell(r, c.key)) is not None
        ),
        lambda c: plain_int(c) and whole(b.cell(r, c.key)) is not None,
    )


def seed_text_in_integer(b: Invalid, r: int) -> Optional[Seeded]:
    column = int_column(b, r)
    if column is None:
        return None
    value = whole(b.cell(r, column.key))
    b.set(r, column.key, f"{value}-{value + 1}")
    return Seeded(
        f"{column.key}='{value}-{value + 1}', a range in a whole-number column",
        [Expect(r, column.key, "error", "Must be a number.")],
    )


def seed_decimal_in_integer(b: Invalid, r: int) -> Optional[Seeded]:
    column = int_column(b, r)
    if column is None:
        return None
    value = f"{whole(b.cell(r, column.key))}.5"
    b.set(r, column.key, value)
    return Seeded(
        f"{column.key}={value}, a decimal in a whole-number column",
        [Expect(r, column.key, "warning", "Will be truncated to a whole number")],
    )


def seed_bad_boolean(b: Invalid, r: int) -> Optional[Seeded]:
    column = b.free(r, lambda c: kind(c) == "bool" and c.key not in RULE_COLUMNS)
    if column is None:
        return None
    b.set(r, column.key, "maybe")
    return Seeded(
        f"{column.key}='maybe', not yes or no",
        [Expect(r, column.key, "error", "Must be 'yes' or 'no'")],
    )


def seed_bad_date(b: Invalid, r: int) -> Optional[Seeded]:
    column = b.free(r, lambda c: kind(c) == "date")
    if column is None:
        return None
    b.set(r, column.key, "2025-13-45")
    return Seeded(
        f"{column.key}='2025-13-45', not dd.mm.yyyy",
        [Expect(r, column.key, "error", "Dates are dd.mm.yyyy")],
    )


def seed_empty_nullable(b: Invalid, r: int) -> Optional[Seeded]:
    column = b.free(r, lambda c: c.nullable and c.key not in RULE_COLUMNS)
    if column is None:
        return None
    b.set(r, column.key, "")
    return Seeded(
        f"{column.key} empty, in a column that accepts NA",
        [Expect(r, column.key, "warning", "Empty cell.")],
    )


def seed_empty_mandatory(b: Invalid, r: int) -> Optional[Seeded]:
    column = b.free(r, lambda c: not c.nullable and c.key not in RULE_COLUMNS)
    if column is None:
        return None
    b.set(r, column.key, "")
    return Seeded(
        f"{column.key} empty, in a mandatory column",
        [Expect(r, column.key, "error", "Mandatory, and the cell is empty.")],
    )


def seed_nan(b: Invalid, r: int) -> Optional[Seeded]:
    def nullable(c):
        return c.nullable and c.key not in RULE_COLUMNS

    column = b.free(
        r, lambda c: nullable(c) and kind(c) == "number", lambda c: nullable(c)
    )
    if column is None:
        return None
    b.set(r, column.key, "NaN")
    return Seeded(
        f"{column.key}='NaN'",
        [Expect(r, column.key, "warning", "NaN is not accepted.")],
    )


def seed_na_mandatory(b: Invalid, r: int) -> Optional[Seeded]:
    def mandatory(c):
        return not c.nullable and c.key not in RULE_COLUMNS

    column = b.free(
        r,
        lambda c: mandatory(c) and kind(c) == "number",
        lambda c: mandatory(c) and kind(c) == "int",
    )
    if column is None:
        return None
    b.set(r, column.key, "NA")
    return Seeded(
        f"{column.key}='NA', in a mandatory number column",
        [Expect(r, column.key, "error", "Mandatory. NA counts as no value.")],
    )


def seed_nr_mandatory_text(b: Invalid, r: int) -> Optional[Seeded]:
    column = b.free(r, lambda c: not c.nullable and kind(c) == "string")
    if column is None:
        return None
    b.set(r, column.key, "NR")
    return Seeded(
        f"{column.key}='NR', in a mandatory text column",
        [Expect(r, column.key, "warning", "Mandatory. NR means not reported")],
    )


def take_id(b: Invalid, r: int) -> Optional[str]:
    if "id" in b.used[r - 1]:
        return None
    b.used[r - 1].add("id")
    return b.cell(r, "id")


def seed_id_with_space(b: Invalid, r: int) -> Optional[Seeded]:
    current = take_id(b, r)
    if current is None:
        return None
    if b.is_ebf:
        value, expect = f"{current} A", "must be a whole number"
    else:
        value, expect = current.replace("-", " "), "contains a space"
    level = "error" if b.is_ebf else "warning"
    b.set(r, "id", value)
    return Seeded(f"id='{value}'", [Expect(r, "id", level, expect)])


def seed_id_with_slash(b: Invalid, r: int) -> Optional[Seeded]:
    current = take_id(b, r)
    if current is None:
        return None
    if b.is_ebf:
        value, expect = f"{current}/2", "must be a whole number"
    else:
        head, _, tail = current.rpartition("-")
        value, expect = f"{head}/{tail}", "cannot be used as a file name"
    b.set(r, "id", value)
    return Seeded(f"id='{value}'", [Expect(r, "id", "error", expect)])


def seed_duplicate_id(b: Invalid, r: int) -> Optional[Seeded]:
    if "id" in b.used[r - 1]:
        return None
    others = [
        t
        for t in range(1, len(b.rows) + 1)
        if t not in (r, b.comma_row) and "id" not in b.used[t - 1]
    ]
    if not others:
        return None
    other = others[0]
    value = take_id(b, other)
    b.set(r, "id", value)
    # The validator flags the second time it sees the id.
    return Seeded(
        f"id='{value}', the id of row {other} again",
        [Expect(max(r, other), "id", "error", "appears more than once")],
    )


def seed_existing_id(b: Invalid, r: int) -> Optional[Seeded]:
    source = b.records[r - 1].source_id
    if source is None or "id" in b.used[r - 1]:
        return None
    # The template's id, when it has no problem of its own.
    if b.is_ebf and not source.isdigit():
        return None
    if not SAFE_ID_PATTERN.fullmatch(source) or " " in source:
        return None
    take_id(b, r)
    b.set(r, "id", source)
    return Seeded(
        f"id='{source}', the id of the real record this row comes from",
        [Expect(r, "id", "error", "already exists in the database")],
    )


def seed_flange_count(b: Invalid, r: int) -> Optional[Seeded]:
    if {"id", "flange_nr_data"} & b.used[r - 1]:
        return None
    declared = b.cell(r, "flange_nr_data")
    if declared not in ("1", "2"):
        return None
    flipped = "1" if declared == "2" else "2"
    b.set(r, "flange_nr_data", flipped)
    b.used[r - 1].add("id")  # the rule finds the F2 file by the id
    # The expectation comes from `flange_expects`, which also covers the rows
    # whose id changed.
    return Seeded(f"flange_nr_data={flipped}, but the curves say {declared}", [])


def seed_has_sem(b: Invalid, r: int) -> Optional[Seeded]:
    if "has_sem" in b.used[r - 1]:
        return None
    b.set(r, "has_sem", "yes")
    return Seeded(
        "has_sem='yes', a field the hub sets",
        [Expect(r, "has_sem", "warning", "Leave it NR in a contribution.")],
    )


def seed_list_without_brackets(b: Invalid, r: int) -> Optional[Seeded]:
    column = b.free(
        r,
        lambda c: (
            kind(c) == "string"
            and is_list_column(c.key)
            and is_number_list(b.cell(r, c.key))
        ),
    )
    if column is None:
        return None
    value = b.cell(r, column.key).strip()[1:-1].strip() or "7.99, 8.01"
    b.set(r, column.key, value)
    return Seeded(
        f"{column.key}='{value}', a list without its brackets",
        [Expect(r, column.key, "warning", "Expected a list of numbers")],
    )


def seeds_for(db: Database) -> list[tuple[str, Callable]]:
    seeds = [
        ("comma", seed_comma),
        ("text", seed_text_in_number),
        ("text", seed_text_in_integer),
        ("decimal", seed_decimal_in_integer),
        ("boolean", seed_bad_boolean),
        ("date", seed_bad_date),
        ("empty", seed_empty_nullable),
        ("empty", seed_empty_mandatory),
        ("nan", seed_nan),
        ("marker", seed_na_mandatory),
        ("marker", seed_nr_mandatory_text),
        ("id", seed_id_with_space),
        ("id", seed_id_with_slash),
        ("id", seed_duplicate_id),
        ("id", seed_existing_id),
    ]
    if db.model is ResidualStress:
        seeds.append(("rule", seed_flange_count))
    if db.model is DuctileFracture:
        seeds.append(("rule", seed_has_sem))
        seeds.append(("rule", seed_list_without_brackets))
    return seeds


def flange_expects(
    rows: list[dict[str, str]], f2_ids: set[str], skip: Optional[int]
) -> list[Expect]:
    """`ResidualStressTableValidator._validate_row`, replayed: flange_nr_data
    must agree with the Distributions_F2 file found by the row's id."""
    expects = []
    for r, row in enumerate(rows, 1):
        declared = (row.get("flange_nr_data") or "").strip()
        specimen = (row.get("id") or "").strip()
        if r == skip or not declared or not specimen:
            continue
        if declared.upper() in MISSING_MARKERS:
            continue
        if declared not in ("1", "2"):
            message = "Expected 1 or 2"
        elif declared == "2" and specimen not in f2_ids:
            message = "Two flange distributions are declared"
        elif declared == "1" and specimen in f2_ids:
            message = "One flange distribution is declared"
        else:
            continue
        expects.append(Expect(r, "flange_nr_data", "warning", message))
    return expects


def seed_invalid(
    db: Database,
    records: list[Record],
    outliers: list[Expect],
    f2_ids: set[str],
) -> tuple[list[dict[str, str]], list[tuple[int, str]], list[Expect]]:
    """One seeded problem per row, in the order of `seeds_for`.

    Seed i goes on row i. When there are more seeds than rows, the rest go as
    a second seed on rows 2, 3... on another column. A seed whose kind of
    column the table does not have is skipped.
    """
    b = Invalid(
        db,
        [dict(record.values) for record in records],
        records,
        [set() for _ in records],
    )
    for expect in outliers:  # keep the range warnings of the clean batch
        b.used[expect.row - 1].add(expect.column)

    count = len(records)
    seeded: set[int] = set()
    notes: list[tuple[int, str]] = []
    expects: list[Expect] = []
    second = 0
    for label, seed in seeds_for(db):
        if label == "comma":
            # On a one-row batch, the comma would leave nothing else to check.
            outcome = seed(b, 1) if count >= 2 else None
            candidates = []
            if outcome:
                seeded.add(1)
                notes.append((1, outcome.note))
                expects.extend(outcome.expects)
            continue
        fresh = [r for r in range(1, count + 1) if r not in seeded][:1]
        others = [r for r in range(1, count + 1) if r != b.comma_row]
        shift = second % len(others) if others else 0
        candidates = fresh + others[shift:] + others[:shift]
        for r in candidates:
            outcome = seed(b, r)
            if outcome:
                if r not in fresh:
                    second += 1
                seeded.add(r)
                notes.append((r, outcome.note))
                expects.extend(outcome.expects)
                break

    expects.extend(e for e in outliers if e.row != b.comma_row)
    if db.model is ResidualStress:
        expects.extend(flange_expects(b.rows, f2_ids, b.comma_row))
    return b.rows, sorted(notes), expects


# --- Measured responses -----------------------------------------------------
#
# The template's real curve when the data repo has it, downsampled. Otherwise a
# synthetic one: not physics, but the right *character* per test. Each kind
# gets its own curve shape and its own magnitudes, both taken from the
# corresponding directory in the data repo. That matters for the UI, whose
# sparkline plots column 1 against column 2 and normalises both axes, so
# specimens sharing a shape look identical no matter how the amplitudes differ.


@dataclass(frozen=True)
class Series:
    """One measured-response directory: where it goes and what it looks like."""

    directory: str
    columns: list[str]  # written in x, y order, the sparkline reads them that way
    shape: str
    x_peak: float
    y_peak: float
    rows: int = 240
    cycles: int = 6
    required: bool = False  # the submission form asks for it (timeseries.ts)
    prefix: str = ""  # of the file name, before the id
    scaled: bool = True  # y follows the row factor (a load, a stress...)

    @property
    def is_second_flange(self) -> bool:
        return self.directory.endswith("Distributions_F2")


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
    """Bilinear kinematic hardening, the standard idealisation of a steel test.

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


def monotonic(
    s: Series, scale: float, profile, x_sign: float = 1.0
) -> list[list[float]]:
    """A single pull to fracture: x grows to its peak, y follows `profile(u)`,
    a fraction of the peak as a function of the progress u in [0, 1]."""
    out = []
    for i in range(s.rows):
        u = i / (s.rows - 1) if s.rows > 1 else 0.0
        out.append([x_sign * s.x_peak * scale * u, s.y_peak * scale * profile(u)])
    return out


def tension(u: float) -> float:
    """Elastic rise, power-law hardening to the ultimate load, then necking."""
    if u < 0.05:
        return 0.75 * u / 0.05
    hardening = min(1.0, (u - 0.05) / 0.6)
    y = 0.75 + 0.25 * (1 - (1 - hardening) ** 2)
    if u > 0.65:
        y -= 0.2 * ((u - 0.65) / 0.35) ** 1.5
    return y


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
    # Coupon: no degradation, strong hardening, loops grow instead of shrinking.
    "stress_strain": lambda s, scale: bilinear(
        s, scale, yield_ratio=0.3, hardening=0.12
    ),
    "ratchet": ratchet,
    "distribution_flange": distribution,
    "distribution_flange_tilted": lambda s, scale: distribution(s, scale, tilt=0.8),
    "distribution_web": lambda s, scale: distribution(s, scale, flip=True),
    "coefficients": coefficients,
    # Coupons and notched bars pulled once to fracture.
    "tension": lambda s, scale: monotonic(s, scale, tension),
    # Radial contraction of the neck: the same pull, x running negative.
    "tension_radial": lambda s, scale: monotonic(s, scale, tension, x_sign=-1.0),
    # Simulation outputs along the elongation: strain accumulates, the Lode
    # angle swings from 1 to -1, the triaxiality climbs from 1/3 as the neck forms.
    "growth": lambda s, scale: monotonic(s, scale, lambda u: u**1.6),
    "lode": lambda s, scale: monotonic(s, scale, lambda u: 1 - 2 * u**0.6),
    "triaxiality": lambda s, scale: monotonic(s, scale, lambda u: 0.33 + 0.67 * u),
}

ROTATION = ["Chord Rotation [rads]", "Moment [kN-mm]"]
DRIFT = ["Total story drift angle (rad)", "Force in the actuator (kN)"]
COORDINATE = ["coordinate", "residual_stress"]
ELONGATION_LOAD = ["Elongation [mm]", "Load [kN]"]
RADIAL_LOAD = ["Radial elongation [mm]", "Load [kN]"]

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
            required=True,
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
            required=True,
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
            required=True,
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
            required=True,
        )
    ],
    "tensile_coupons": [
        Series(
            "material/tensile_coupons/stress_strain",
            ["strain_eng", "Stress_eng"],
            "tension",
            x_peak=0.25,
            y_peak=520,
            rows=150,
            required=True,
        )
    ],
    "eccentric_braced_frames": [
        # Link shear V against the total link rotation gamma_t, cycled to failure.
        Series(
            "eccentric_braced_frames/processed_data",
            ["gamma_t", "V"],
            "hysteresis",
            x_peak=0.11,
            y_peak=300,
            rows=400,
            cycles=12,
            required=True,
            prefix="id",
        )
    ],
    "ductile_fracture": [
        # The measured pull, and the calibrated simulation of the same test.
        Series(
            "material/ductile_fracture/force_elongation",
            ELONGATION_LOAD,
            "tension",
            x_peak=0.64,
            y_peak=10,
            rows=400,
            required=True,
        ),
        Series(
            "material/ductile_fracture/force_elongation_simulation",
            ELONGATION_LOAD,
            "tension",
            x_peak=0.64,
            y_peak=10,
            rows=200,
        ),
        Series(
            "material/ductile_fracture/force_radial",
            RADIAL_LOAD,
            "tension_radial",
            x_peak=1.0,
            y_peak=10,
            rows=400,
        ),
        Series(
            "material/ductile_fracture/force_radial_simulation",
            RADIAL_LOAD,
            "tension_radial",
            x_peak=0.9,
            y_peak=10,
            rows=200,
        ),
        Series(
            "material/ductile_fracture/equivalent_plastic_strain_elongation_simulation",
            ["Elongation [mm]", "Equivalent plastic strain"],
            "growth",
            x_peak=0.64,
            y_peak=4.6,
            rows=200,
        ),
        # An angle and a stress ratio: they do not grow with the specimen.
        Series(
            "material/ductile_fracture/lode_angle_elongation_simulation",
            ["Elongation [mm]", "Lode angle"],
            "lode",
            x_peak=0.64,
            y_peak=1.0,
            rows=200,
            scaled=False,
        ),
        Series(
            "material/ductile_fracture/triaxiality_elongation_simulation",
            ["Elongation [mm]", "Triaxiality"],
            "triaxiality",
            x_peak=0.64,
            y_peak=1.0,
            rows=200,
            scaled=False,
        ),
    ],
    "residual_stresses": [
        Series(
            "residual_stresses/Distributions/Distributions_F1",
            COORDINATE,
            "distribution_flange",
            x_peak=297,
            y_peak=35,
            rows=13,
            required=True,
        ),
        # Written only for a record whose flange_nr_data is 2.
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
            required=True,
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


def wanted(series: Series, flange_nr_data) -> bool:
    if series.is_second_flange:
        return str(flange_nr_data).strip() == "2"
    return True


def needed(series: Series) -> bool:
    """A second flange, once declared, must be there like a required series."""
    return series.required or series.is_second_flange


class CurveSource:
    """The real curves of the data repo, found by the template's id."""

    def __init__(self, data_dir: Optional[Path]):
        self.data_dir = data_dir
        self._names: dict[Path, set[str]] = {}

    def path(self, series: Series, source_id: Optional[str]) -> Optional[Path]:
        if self.data_dir is None or source_id is None:
            return None
        directory = self.data_dir / series.directory
        if directory not in self._names:
            self._names[directory] = (
                {p.name for p in directory.iterdir()} if directory.is_dir() else set()
            )
        name = f"{series.prefix}{source_id}.csv"
        return directory / name if name in self._names[directory] else None

    def score(self, db: Database, row: dict) -> tuple[int, int]:
        """How many curves the record has: the required ones, then all."""
        name = next(n for n, d in DATABASES.items() if d is db)
        found = [
            (series.required, self.path(series, str(row["id"])) is not None)
            for series in TIME_SERIES.get(name, [])
            if wanted(series, row.get("flange_nr_data"))
        ]
        return (
            sum(1 for required, real in found if required and real),
            sum(1 for _, real in found if real),
        )


def downsample(rows: list, max_rows: int) -> list:
    """Every k-th row, at most `max_rows` of them, and always the last one."""
    if len(rows) <= max_rows:
        return rows
    stride = math.ceil((len(rows) - 1) / (max_rows - 1))
    picked = rows[::stride]
    if picked[-1] is not rows[-1]:
        picked.append(rows[-1])
    return picked


def scaled_cell(text: str, factor: float) -> str:
    value = Decimal(text.strip())
    places = max(0, -value.as_tuple().exponent)
    moved = (value * Decimal(str(round(factor, 6)))).quantize(
        Decimal(1).scaleb(-places)
    )
    return plain(abs(moved) if moved == 0 else moved)


def real_curve(
    path: Path, series: Series, max_rows: int, factor: float
) -> Optional[str]:
    """The data repo's file: header line as is, rows downsampled, y scaled.

    Rows where a column the validator needs is not a plain number are dropped
    (NaN readings, empty lines). Returns None when nothing usable is left.
    """
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    header_line = lines[0]
    header = next(csv.reader([header_line]))
    try:
        indexes = [header.index(name) for name in series.columns]
    except ValueError:
        return None
    rows = [
        cells
        for cells in csv.reader(lines[1:])
        if all(i < len(cells) and number(cells[i]) is not None for i in indexes)
    ]
    if len(rows) < 2:
        return None
    y = indexes[1] if len(indexes) > 1 and series.scaled else None
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    for cells in downsample(rows, max_rows):
        if y is not None:
            cells = list(cells)
            cells[y] = scaled_cell(cells[y], factor)
        writer.writerow(cells)
    return header_line + "\n" + out.getvalue()


def synthetic_curve(series: Series, factor: float) -> str:
    shaped = replace(series, y_peak=series.y_peak * factor)
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(series.columns)
    for row in SHAPES[series.shape](shaped, 1.0):
        writer.writerow([f"{value:.6f}" for value in row[: len(series.columns)]])
    return out.getvalue()


@dataclass
class CurveCount:
    real: int = 0
    synthetic: int = 0
    none: int = 0
    rows: list[int] = field(default_factory=list)


def write_curves(
    root: Path,
    name: str,
    records: list[Record],
    curves: CurveSource,
    max_rows: int,
) -> tuple[dict[str, CurveCount], set[str]]:
    """Write each record's curves, named after its demo id.

    The real file when the data repo has one. Otherwise a synthetic one, but
    only for a series the form requires, or when the template has no real
    curve at all: an optional curve the real test never had stays missing.
    Returns the counts per directory and the ids that got a second flange.
    """
    counts: dict[str, CurveCount] = {}
    second_flange: set[str] = set()
    for record in records:
        series_list = [
            s
            for s in TIME_SERIES.get(name, [])
            if wanted(s, record.values.get("flange_nr_data"))
        ]
        sources = [curves.path(s, record.source_id) for s in series_list]
        any_real = any(sources)
        for series, source in zip(series_list, sources):
            count = counts.setdefault(series.directory, CurveCount())
            text = (
                real_curve(source, series, max_rows, record.factor) if source else None
            )
            if text is not None:
                count.real += 1
            elif needed(series) or not any_real:
                text = synthetic_curve(series, record.factor)
                count.synthetic += 1
            else:
                count.none += 1
                continue
            count.rows.append(text.count("\n") - 1)
            target = (
                root / series.directory / f"{series.prefix}{record.values['id']}.csv"
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("w", newline="", encoding="utf-8") as handle:
                handle.write(text)
            if series.is_second_flange:
                second_flange.add(record.values["id"])
    return counts, second_flange


def write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        handle.write(buffer.getvalue().replace(COMMA_TOKEN, "3,5"))


# --- Self-check -----------------------------------------------------------------


def compare(result, expects: list[Expect]) -> list[str]:
    """Each expected message once, and nothing else."""
    remaining = list(expects)
    problems = []
    actual = [("error", e) for e in result.errors] + [
        ("warning", w) for w in result.warnings
    ]
    for level, item in actual:
        match = next(
            (
                e
                for e in remaining
                if e.row == item.row
                and e.column == item.column
                and e.level == level
                and e.message in item.message
            ),
            None,
        )
        if match:
            remaining.remove(match)
        else:
            problems.append(
                f"unexpected {level}, row {item.row} {item.column}: {item.message}"
            )
    for e in remaining:
        problems.append(f"missing {e.level}, row {e.row} {e.column}: {e.message}")
    return problems


def self_check(
    db: Database, root: Path, clean: list[Expect], invalid: list[Expect]
) -> list[str]:
    """Run the real validator on both files, the way a submission does.

    The clean folder must give only the seeded range warnings, curves
    included. The invalid file (put in place of the clean one) must give each
    seeded message on its row. Its curves are not compared: the id seeds leave
    some of them without a record, on purpose.
    """
    folder = Path(db.csv_path).parent
    primary = Path(db.csv_path).name
    problems = []
    for variant, expects in (("clean", clean), ("invalid", invalid)):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / folder
            shutil.copytree(
                root / folder, target, ignore=shutil.ignore_patterns("*.invalid.csv")
            )
            if variant == "invalid":
                shutil.copyfile(
                    root / Path(db.csv_path).with_suffix(".invalid.csv"),
                    target / primary,
                )
            # The validator logs every result; the comparison says it better.
            logging.disable(logging.CRITICAL)
            try:
                results = validate_all(
                    db.input_type, [tmp], cpu=1, check_duplicate_ids=True
                )
            finally:
                logging.disable(logging.NOTSET)
        main = [r for r in results if r.filename == primary]
        if len(main) != 1:
            problems.append(f"{variant}: the validator did not read {primary}")
            continue
        problems += [f"{variant}: {p}" for p in compare(main[0], expects)]
        if variant == "clean":
            for result in results:
                if result is main[0]:
                    continue
                for level, items in (
                    ("error", result.errors),
                    ("warning", result.warnings),
                ):
                    problems += [
                        f"clean: {level} in {result.filename}: {item}" for item in items
                    ]
    return problems


# --- Main -------------------------------------------------------------------------


def clear_output(root: Path, db: Database) -> None:
    """Remove the CSVs of the last run: a curve whose record is gone would fail
    the foreign-key check when the folder is dropped in the form."""
    folder = root / Path(db.csv_path).parent
    if folder.is_dir():
        for path in folder.rglob("*.csv"):
            path.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
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
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="random seed: the same seed and data give the same files (default: 0)",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        help="the resslab-hub-data checkout, for the real curves",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=500,
        help="rows kept from a real curve (default: 500)",
    )
    parser.add_argument(
        "--no-check",
        action="store_true",
        help="do not run the validator on the result",
    )
    args = parser.parse_args()
    count = max(1, args.experiments)
    outliers = max(0, min(args.outliers, count))
    max_rows = max(2, args.max_rows)

    data_dir = args.data_dir
    if data_dir is not None and not data_dir.is_dir():
        print(f"no data repo at {data_dir}: synthetic curves only")
        data_dir = None
    curves = CurveSource(data_dir)

    root = Path(__file__).resolve().parent
    engine = create_engine(url, echo=False)
    summary: list[str] = []
    failed: list[str] = []

    for name, db in DATABASES.items():
        model = db.model
        rng = random.Random(f"{args.seed}:{name}")
        columns = [c.key for c in contributed_columns(model)]
        try:
            stats = range_stats(model, engine)
            all_rows = load_rows(model, engine)
            reason = "the table is empty"
        except Exception as exc:  # no database: fall back to type-based values
            stats, all_rows = {}, []
            reason = f"no database ({type(exc).__name__})"

        templates = [row for row in all_rows if usable(model, row)]
        ebf_base = max(
            (int(row["id"]) for row in all_rows if str(row["id"]).isdigit()),
            default=0,
        )
        if templates:
            records = from_templates(
                db, templates, all_rows, count, stats, rng, curves, ebf_base
            )
        else:
            if all_rows:
                reason = f"none of its {len(all_rows)} records is complete"
            records = from_types(db, count, stats, rng, ebf_base)

        outlier_expects, outlier_notes = seed_outliers(model, records, stats, outliers)

        clear_output(root, db)
        curve_counts, second_flange = write_curves(
            root, name, records, curves, max_rows
        )
        stem = Path(db.csv_path)
        write_csv(root / stem, columns, [r.values for r in records])
        bad_rows, seed_notes, invalid_expects = seed_invalid(
            db, records, outlier_expects, second_flange
        )
        write_csv(root / stem.with_suffix(".invalid.csv"), columns, bad_rows)

        clean_expects = list(outlier_expects)
        if model is ResidualStress:
            clean_expects += flange_expects(
                [r.values for r in records], second_flange, None
            )

        summary.append(
            f"{name}: {count} experiments x {len(columns)} columns -> {stem}"
            f"  [{records[0].values['id']} ... {records[-1].values['id']}]"
        )
        if templates:
            sources = {r.source_id for r in records}
            summary.append(
                f"    values: from {len(sources)} real records "
                f"({len(templates)} of {len(all_rows)} usable), "
                f"numbers moved by up to 7 %"
            )
        else:
            summary.append(f"    values: fixed per column type, {reason}")
        for note in outlier_notes:
            summary.append(f"    warning: {note}")
        if stats and not outlier_notes:
            summary.append("    warning: none seeded (--outliers 0)")
        if not stats:
            hint = "" if all_rows else " (run `make upload-data`)"
            summary.append(
                f"    warning: none possible, no column has {RANGE_MIN_COUNT} "
                f"values in the database yet{hint}"
            )
        for directory, c in curve_counts.items():
            longest = max(c.rows) if c.rows else 0
            missing = f", {c.none} not in the real test" if c.none else ""
            summary.append(
                f"    curves: {directory}: {c.real} real, {c.synthetic} "
                f"synthetic{missing} (up to {longest} rows)"
            )
        for row, note in seed_notes:
            summary.append(f"    invalid: row {row}: {note}")

        if not args.no_check:
            problems = self_check(db, root, clean_expects, invalid_expects)
            if problems:
                failed.append(name)
                summary.append(f"    check: {len(problems)} differences")
                summary.extend(f"      {p}" for p in problems)
            else:
                summary.append("    check: ok")

    print("\n".join(summary))
    if failed:
        raise SystemExit(f"self-check failed for: {', '.join(failed)}")


if __name__ == "__main__":
    main()
