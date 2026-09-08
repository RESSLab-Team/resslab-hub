"""Blow a real database up to N rows, keeping the shape of the real data.

The dashboard benchmark (#354) needs a table big enough to hurt. Our biggest
one has 371 rows, so we have to invent the rest. The two generators we already
have are not usable here:

  * ``sample-data/generate.py`` gives every string column one constant value and
    spreads the numerics linearly over the observed range,
  * ``benchmark/benchmark.py``'s ``write_brace_csv`` varies three columns.

Both are fine for what they do (validator branches, backend throughput), but a
dashboard measured on one-value facets is a lie: the treemap gets one tile, the
counts one bar, the filter rail one option per field. What costs time in the
browser is the number of distinct values, the share of empty cells and the
spread of the numerics -- so we resample the real CSV instead of inventing it.

For every output row, every column draws a value from the real column, on its
own. Column by column the result keeps the real distinct values, their
frequencies and the real share of empty cells; row by row the combinations are
new, which is what we want (a benchmark, not a plausible experiment). Numeric
columns get a small jitter so 10 000 rows do not collapse onto 300 distinct
values and make the histograms and the range filters look cheaper than they are.

Types come from the folder's ``*_data_dictionary.csv`` (its ``type`` column),
which sits next to the data and covers every column, so this script needs no
database, no settings and no ORM import. Unknown types fall back to sniffing
the values.

Usage (from ``backend/``)::

    uv run python -m benchmark.bootstrap_rows braces --rows 10000
    uv run python -m benchmark.bootstrap_rows connections --rows 10000 --seed 354

Then upload the file it prints::

    uv run python -m resslab_hub.data.uploader brace \
        .benchmark-tmp/braces/steel_braces.csv

Only ever point that at a throwaway database (a worktree clone, ``make
db-branch`` to get it back): the uploader deletes the ids that are not in the
CSV, so a bootstrap upload replaces the real rows.
"""

from __future__ import annotations

import argparse
import csv
import os
import random
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_DEFAULT_DATA_DIR = _BACKEND_DIR.parent.parent / "resslab-hub-data"


@dataclass(frozen=True)
class Database:
    """Where a database's CSV lives, and how to upload the bootstrapped copy."""

    csv_path: str  # relative to the data repo, the layout the uploader expects
    prefix: str  # id prefix, so bootstrapped rows are obvious in the UI
    upload_type: str  # the `Type` value of resslab_hub.data.uploader

    @property
    def dictionary_path(self) -> str:
        return self.csv_path.replace(".csv", "_data_dictionary.csv")


# Same keys as sample-data/generate.py, same paths as the data repo.
DATABASES: dict[str, Database] = {
    "braces": Database("braces/steel_braces.csv", "BRC", "brace"),
    "columns": Database("columns/steel_columns.csv", "COL", "column"),
    "connections": Database("connections/connections.csv", "CON", "connection"),
    "hss_columns": Database("hss_columns/hss_columns.csv", "HSS", "hss-column"),
    "cyclic_coupons": Database(
        "material/cyclic_coupons/steel_material.csv", "MAT", "material"
    ),
    "tensile_coupons": Database(
        "material/tensile_coupons/tensile_coupons.csv", "TC", "tensile-coupon"
    ),
    "ductile_fracture": Database(
        "material/ductile_fracture/ductile_fracture.csv", "DF", "ductile-fracture"
    ),
    "residual_stresses": Database(
        "residual_stresses/residual_stresses.csv", "RS", "residual-stress"
    ),
    "eccentric_braced_frames": Database(
        "eccentric_braced_frames/eccentric_braced_frames.csv",
        "EBF",
        "eccentric-braced-frame",
    ),
}

# Data dictionary `type` values that hold a number. Anything else (String, Date,
# Boolean, a typo like "SmallSmallInteger") is resampled as text.
_NUMERIC_TYPES = {
    "numeric",
    "decimalfloat",
    "smallinteger",
    "biginteger",
    "integer",
}
_INTEGER_TYPES = {"smallinteger", "biginteger", "integer"}

# Columns whose numbers must not be jittered: a year moved by 5 % lands in the
# middle ages, and the derived flags are 0/1.
_NO_JITTER = re.compile(r"(^date$|year|_count$|^has_|_flag$)")

# What the READMEs allow in place of a value, mirroring MISSING_MARKERS in
# resslab_hub/data/validator.py (kept local so this script needs no settings).
# The uploader turns them into NULL, so they must survive the resampling as-is.
_MISSING_MARKERS = {"NA", "NR", "NAN"}

JITTER = Decimal("0.05")  # +/- 5 % around the real value


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        header = list(reader.fieldnames or [])
        return header, list(reader)


def column_types(path: Path, header: list[str]) -> dict[str, str]:
    """`column_name` -> lowered dictionary type, for the columns it declares."""
    if not path.exists():
        return {}
    _, rows = read_csv(path)
    declared = {
        row["column_name"]: (row.get("type") or "").strip().lower()
        for row in rows
        if row.get("column_name")
    }
    return {name: declared[name] for name in header if name in declared}


def missing(value: str) -> bool:
    """Empty, or one of the markers the data repo uses for "no value"."""
    text = value.strip()
    return not text or text.upper() in _MISSING_MARKERS


def looks_numeric(values: list[str]) -> bool:
    """Fallback when the dictionary says nothing: do the values parse?

    The `NA` / `NR` markers are skipped, else every numeric column that has one
    would read as text and lose its jitter.
    """
    seen = 0
    for value in values:
        if missing(value):
            continue
        try:
            Decimal(value)
        except InvalidOperation:
            return False
        seen += 1
    return seen > 0


def decimals(value: str) -> int:
    _, _, fraction = value.strip().partition(".")
    return len(fraction)


def jitter(value: str, integer: bool, rng: random.Random) -> str:
    """Nudge a number by up to +/- 5 %, keeping the source's number of decimals."""
    try:
        number = Decimal(value.strip())
    except InvalidOperation:
        return value
    factor = Decimal(1) + JITTER * Decimal(str(rng.uniform(-1.0, 1.0)))
    nudged = number * factor
    if integer:
        return str(int(nudged))
    places = decimals(value)
    quantum = Decimal(1).scaleb(-places) if places else Decimal(1)
    return format(nudged.quantize(quantum), "f")


def bootstrap(
    header: list[str],
    rows: list[dict[str, str]],
    types: dict[str, str],
    count: int,
    prefix: str,
    rng: random.Random,
) -> list[dict[str, str]]:
    """One independent draw per column, so each column keeps its own shape."""
    pools = {name: [row.get(name, "") or "" for row in rows] for name in header}

    numeric: dict[str, bool] = {}
    integer: dict[str, bool] = {}
    for name in header:
        declared = types.get(name)
        if declared is None:
            is_numeric = looks_numeric(pools[name])
            is_integer = is_numeric and all(
                decimals(v) == 0 for v in pools[name] if not missing(v)
            )
        else:
            is_numeric = declared in _NUMERIC_TYPES
            is_integer = declared in _INTEGER_TYPES
        numeric[name] = is_numeric and not _NO_JITTER.search(name)
        integer[name] = is_integer

    out: list[dict[str, str]] = []
    for index in range(1, count + 1):
        row: dict[str, str] = {}
        for name in header:
            if name == "id":
                row[name] = f"BENCH-{prefix}-{index:05d}"
                continue
            value = rng.choice(pools[name])
            if numeric[name] and not missing(value):
                value = jitter(value, integer[name], rng)
            row[name] = value
        out.append(row)
    return out


def write_csv(path: Path, header: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("database", choices=sorted(DATABASES), help="which database")
    parser.add_argument("--rows", type=int, default=10_000, help="rows to write")
    parser.add_argument("--seed", type=int, default=354, help="rng seed, for repeats")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(os.environ.get("RESSLAB_DATA_DIR", _DEFAULT_DATA_DIR)),
        help="the resslab-hub-data checkout to resample from",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=_BACKEND_DIR / ".benchmark-tmp",
        help="output root; the CSV keeps its path inside the data repo",
    )
    args = parser.parse_args()

    database = DATABASES[args.database]
    source = args.data_dir / database.csv_path
    if not source.exists():
        raise SystemExit(f"no such CSV: {source} (set --data-dir or RESSLAB_DATA_DIR)")

    header, rows = read_csv(source)
    if not rows:
        raise SystemExit(f"{source} has no data rows to resample")
    types = column_types(args.data_dir / database.dictionary_path, header)

    rng = random.Random(args.seed)
    generated = bootstrap(header, rows, types, args.rows, database.prefix, rng)
    target = args.out / database.csv_path
    write_csv(target, header, generated)

    untyped = [name for name in header if name not in types]
    print(f"{target}: {len(generated)} rows, {len(header)} columns")
    print(f"  resampled from {source} ({len(rows)} rows), seed {args.seed}")
    if untyped:
        print(f"  types sniffed for {len(untyped)} column(s): {', '.join(untyped)}")
    print("\nUpload it into a throwaway database with:\n")
    print(
        f"  uv run python -m resslab_hub.data.uploader {database.upload_type} {target}"
    )


if __name__ == "__main__":
    main()
