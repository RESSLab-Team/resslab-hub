"""Put a residual stress delivery of the lab into the data repo (#228).

The lab sends the residual stress database as a folder (a zip on the issue):
the main table, its dictionary, ``Distributions/`` and ``QP_Coefficients/``.
This script writes it into ``residual_stresses/`` of the data repo, with the
cleaning the hub and the data CI need, and nothing else:

- every CSV in UTF-8, LF line endings, a final newline. The main table of the
  2026-11-17 delivery mixes two encodings: the old rows are UTF-8 and the new
  ones cp1252, so each line is decoded alone. Windows quote characters stored
  as C1 control characters (U+0093 for a left double quote) are fixed too;
- ``steel-web`` becomes ``steel_web`` (the hub builds Python names from the
  column names);
- ``data_curation_status`` is kept: the old rows keep their value, the new
  rows are ``verified`` (they come from the lab's own curator);
- the distribution header ``Coordinate,Residual Stress`` becomes
  ``coordinate,residual_stress``, the one spelling of the repo;
- an empty (0 byte) file is not copied: the repo file, if any, stays;
- the dictionary uses ``True``/``False``, ``-`` for "no unit", and gets its
  ``data_curation_status`` row back.

The old records must not change: their cells and their series files are
compared with the base commit of the data repo (``origin/main``), and any
difference stops the script, except the cells listed in ``KEEP_REPO_CELLS``.

Usage (from ``backend/``)::

    uv run python data/import_residual_stress_delivery.py <delivery> <data repo>

``<delivery>`` is the unpacked folder (it holds ``residual_stresses.csv``).
Its scripts are never run. The script ends with its own checks of the written
folder and exits 1 when one fails.
"""

from __future__ import annotations

import argparse
import csv
import io
import subprocess
import sys
from pathlib import Path

from resslab_hub.data.residual_stress_qp import (
    BUILT_UP_QP_COLUMNS,
    HOT_ROLLED_QP_ROWS,
    QP_COEFFICIENT_COLUMN,
)

FOLDER = "residual_stresses"
MAIN_CSV = "residual_stresses.csv"
DICTIONARY_CSV = "residual_stresses_data_dictionary.csv"
DISTRIBUTION_DIRS = (
    "Distributions/Distributions_F1",
    "Distributions/Distributions_F2",
    "Distributions/Distributions_W1",
)
QP_DIR = "QP_Coefficients"
STATUS_COLUMN = "data_curation_status"
NEW_ROW_STATUS = "verified"

COLUMN_RENAMES = {"steel-web": "steel_web"}
DISTRIBUTION_HEADER = "coordinate,residual_stress"
DISTRIBUTION_HEADER_ALIASES = {"Coordinate,Residual Stress": DISTRIBUTION_HEADER}
NO_UNIT = "-"
UNIT_RENAMES = {"None": NO_UNIT, "NR": NO_UNIT, "": NO_UNIT}
NULLABLE_RENAMES = {"TRUE": "True", "FALSE": "False"}
GROUP_RENAMES = {"Fabrication detail": "Fabrication details"}

# Old cells the delivery changed, where the repo keeps its own text until the
# lab answers (question on #228): "of Europe hot-rolled" in place of "of
# European hot-rolled" looks like a find and replace by accident.
KEEP_REPO_CELLS = {
    ("Sousa_and_Lignos_2017_HEB500_17", "reference"),
    ("Sousa_and_Lignos_2017_IPE400_18", "reference"),
    ("Sousa_and_Lignos_2017_HEM300_19", "reference"),
}


class ImportError_(Exception):
    """A problem in the delivery that the script does not fix on its own."""


def fix_c1(text: str) -> str:
    """Turn C1 control characters back into the cp1252 character they stand for.

    A cp1252 file read as Latin-1 and saved as UTF-8 keeps a left double quote
    as U+0093. Bytes that cp1252 does not define stay as they are.
    """

    def fixed(char: str) -> str:
        if not 0x80 <= ord(char) <= 0x9F:
            return char
        try:
            return bytes([ord(char)]).decode("cp1252")
        except UnicodeDecodeError:
            return char

    return "".join(fixed(char) for char in text)


def decode_lines(raw: bytes) -> str:
    """Decode a file line by line: UTF-8, else cp1252. LF, no BOM."""
    raw = raw.removeprefix(b"\xef\xbb\xbf").replace(b"\r\n", b"\n")
    lines = []
    for line in raw.split(b"\n"):
        try:
            lines.append(line.decode("utf-8"))
        except UnicodeDecodeError:
            lines.append(line.decode("cp1252"))
    return fix_c1("\n".join(lines))


def read_table(text: str) -> tuple[list[str], list[list[str]]]:
    rows = [row for row in csv.reader(io.StringIO(text)) if any(cell for cell in row)]
    return rows[0], rows[1:]


def write_table(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(headers)
    writer.writerows(rows)
    path.write_text(buffer.getvalue(), encoding="utf-8", newline="")


def with_final_newline(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


class Base:
    """The data repo at its base commit, read through git."""

    def __init__(self, repo: Path, ref: str) -> None:
        self.repo = repo
        self.ref = ref
        listed = subprocess.run(
            ["git", "-C", str(repo), "ls-tree", "-r", "--name-only", ref, FOLDER],
            check=True,
            capture_output=True,
            text=True,
        )
        self.paths = set(listed.stdout.split())

    def read(self, relative: str) -> bytes | None:
        """A file under ``residual_stresses/``, or None when the base has none."""
        path = f"{FOLDER}/{relative}"
        if path not in self.paths:
            return None
        return subprocess.run(
            ["git", "-C", str(self.repo), "show", f"{self.ref}:{path}"],
            check=True,
            capture_output=True,
        ).stdout


def is_built_up(profile_type: str) -> bool:
    return "built-up" in profile_type.strip().lower()


def import_main_table(delivery: Path, base: Base) -> tuple[list[str], list[list[str]]]:
    headers, rows = read_table(decode_lines((delivery / MAIN_CSV).read_bytes()))
    headers = [COLUMN_RENAMES.get(name.strip(), name.strip()) for name in headers]
    if len(set(headers)) != len(headers):
        raise ImportError_(f"{MAIN_CSV}: a column name is repeated")
    for number, row in enumerate(rows, start=2):
        if len(row) != len(headers):
            raise ImportError_(
                f"{MAIN_CSV} line {number}: {len(row)} cells, {len(headers)} columns"
            )
    if STATUS_COLUMN in headers:
        # The hub sets it: the repo value wins, a new row is verified (below).
        index = headers.index(STATUS_COLUMN)
        headers.pop(index)
        for row in rows:
            row.pop(index)

    base_headers, base_rows = read_table(decode_lines(base.read(MAIN_CSV) or b""))
    old = {row[0]: dict(zip(base_headers, row)) for row in base_rows}
    missing_columns = set(base_headers) - set(headers) - {STATUS_COLUMN}
    if missing_columns:
        raise ImportError_(f"{MAIN_CSV}: columns removed: {sorted(missing_columns)}")

    id_index = headers.index("id")
    ids = [row[id_index] for row in rows]
    if len(set(ids)) != len(ids):
        raise ImportError_(f"{MAIN_CSV}: an id is repeated")
    removed = set(old) - set(ids)
    if removed:
        raise ImportError_(f"{MAIN_CSV}: records removed: {sorted(removed)}")

    problems = []
    for row in rows:
        record = row[id_index]
        if record not in old:
            row.append(NEW_ROW_STATUS)
            continue
        for index, name in enumerate(headers):
            if name not in old[record] or row[index] == old[record][name]:
                continue
            if (record, name) in KEEP_REPO_CELLS:
                print(f"kept the repo value of {record}.{name}")
                row[index] = old[record][name]
            else:
                before, after = old[record][name], row[index]
                problems.append(f"{record}.{name}: {before!r} -> {after!r}")
        row.append(old[record].get(STATUS_COLUMN, NEW_ROW_STATUS))
    if problems:
        raise ImportError_("old cells changed:\n  " + "\n  ".join(problems))
    return headers + [STATUS_COLUMN], rows


def import_dictionary(
    delivery: Path, base: Base, columns: list[str]
) -> tuple[list[str], list[dict]]:
    text = decode_lines((delivery / DICTIONARY_CSV).read_bytes())
    reader = csv.DictReader(io.StringIO(text))
    fields = list(reader.fieldnames or [])
    entries = []
    for entry in reader:
        name = entry["column_name"].strip()
        entry["column_name"] = COLUMN_RENAMES.get(name, name)
        entry["unit"] = UNIT_RENAMES.get(entry["unit"].strip(), entry["unit"].strip())
        nullable = entry["nullable"].strip()
        entry["nullable"] = NULLABLE_RENAMES.get(nullable, nullable)
        group = entry["group"].strip()
        entry["group"] = GROUP_RENAMES.get(group, group)
        entries.append(entry)

    base_reader = csv.DictReader(io.StringIO(decode_lines(base.read(DICTIONARY_CSV))))
    status = [entry for entry in base_reader if entry["column_name"] == STATUS_COLUMN]
    if not any(entry["column_name"] == STATUS_COLUMN for entry in entries):
        entries.extend(status)

    named = [entry["column_name"] for entry in entries]
    if sorted(named) != sorted(columns):
        raise ImportError_(
            f"{DICTIONARY_CSV} and {MAIN_CSV} disagree: "
            f"{sorted(set(named) ^ set(columns))}"
        )
    bad = [e["column_name"] for e in entries if e["nullable"] not in ("True", "False")]
    if bad:
        raise ImportError_(f"{DICTIONARY_CSV}: nullable is not True or False: {bad}")
    return fields, entries


def write_dictionary(path: Path, fields: list[str], entries: list[dict]) -> None:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(entries)
    path.write_text(buffer.getvalue(), encoding="utf-8", newline="")


def clean_series(relative: str, raw: bytes, profile_type: str) -> str:
    """The cleaned text of one series file, or ImportError_."""
    try:
        text = raw.removeprefix(b"\xef\xbb\xbf").replace(b"\r\n", b"\n").decode()
    except UnicodeDecodeError as error:
        raise ImportError_(f"{relative}: not UTF-8 ({error})")
    lines = text.rstrip("\n").split("\n")
    header = lines[0].strip()
    if relative.startswith(QP_DIR):
        names = [name.strip() for name in header.split(",")]
        if is_built_up(profile_type):
            expected = (list(BUILT_UP_QP_COLUMNS), 1)
        else:
            expected = ([QP_COEFFICIENT_COLUMN], HOT_ROLLED_QP_ROWS)
        if (names, len(lines) - 1) != expected:
            raise ImportError_(
                f"{relative}: {len(lines) - 1} rows under {header!r}, a "
                f"{profile_type} record expects {expected[1]} under "
                f"{','.join(expected[0])!r}"
            )
    else:
        header = DISTRIBUTION_HEADER_ALIASES.get(header, header)
        if header != DISTRIBUTION_HEADER:
            raise ImportError_(f"{relative}: unknown header {lines[0]!r}")
        lines[0] = header
    return "\n".join(lines) + "\n"


def import_series(
    delivery: Path, target: Path, base: Base, profile_types: dict[str, str]
) -> list[str]:
    """Write the series files; return the empty files that were left out."""
    empty = []
    problems = []
    for directory in DISTRIBUTION_DIRS + (QP_DIR,):
        (target / directory).mkdir(parents=True, exist_ok=True)
        for source in sorted((delivery / directory).glob("*.csv")):
            relative = f"{directory}/{source.name}"
            record = source.stem
            if record not in profile_types:
                problems.append(f"{relative}: no record {record} in {MAIN_CSV}")
                continue
            raw = source.read_bytes()
            if not raw.strip():
                empty.append(relative)
                continue
            try:
                text = clean_series(relative, raw, profile_types[record])
            except ImportError_ as error:
                problems.append(str(error))
                continue
            old = base.read(relative)
            if old is not None and old.decode() != text:
                problems.append(f"{relative}: differs from the repo")
                continue
            (target / relative).write_text(text, encoding="utf-8", newline="")
    if problems:
        raise ImportError_("series files:\n  " + "\n  ".join(problems))
    return empty


def check_folder(target: Path, base: Base) -> list[str]:
    """The checks of the written folder. Returns the problems found."""
    problems = []
    for path in sorted(target.rglob("*.csv")):
        relative = path.relative_to(target).as_posix()
        raw = path.read_bytes()
        if not raw:
            problems.append(f"{relative}: empty")
            continue
        if b"\r" in raw:
            problems.append(f"{relative}: CR in the file")
        if not raw.endswith(b"\n"):
            problems.append(f"{relative}: no final newline")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            problems.append(f"{relative}: not UTF-8")
            continue
        if any(0x80 <= ord(char) <= 0x9F for char in text):
            problems.append(f"{relative}: C1 control character")

    headers, rows = read_table((target / MAIN_CSV).read_text(encoding="utf-8"))
    ids = [row[headers.index("id")] for row in rows]
    if len(set(ids)) != len(ids):
        problems.append(f"{MAIN_CSV}: an id is repeated")
    records = dict(zip(ids, rows))
    profile_index = headers.index("profile_type")

    for directory in DISTRIBUTION_DIRS + (QP_DIR,):
        for path in sorted((target / directory).glob("*.csv")):
            relative = f"{directory}/{path.name}"
            if path.stem not in records:
                problems.append(f"{relative}: no record {path.stem}")
                continue
            try:
                profile = records[path.stem][profile_index]
                clean_series(relative, path.read_bytes(), profile)
            except ImportError_ as error:
                problems.append(str(error))

    base_headers, base_rows = read_table(decode_lines(base.read(MAIN_CSV)))
    for base_row in base_rows:
        record = base_row[0]
        if record not in records:
            problems.append(f"{MAIN_CSV}: record {record} removed")
            continue
        row = dict(zip(headers, records[record]))
        for name, value in zip(base_headers, base_row):
            if row.get(name) != value:
                problems.append(f"{MAIN_CSV}: {record}.{name} changed")

    for path in sorted(base.paths):
        relative = path.removeprefix(f"{FOLDER}/")
        if not relative.startswith(DISTRIBUTION_DIRS + (QP_DIR,)):
            continue
        written = target / relative
        if not written.is_file():
            problems.append(f"{relative}: removed")
        elif written.read_bytes() != base.read(relative):
            problems.append(f"{relative}: changed")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("delivery", type=Path, help="unpacked delivery folder")
    parser.add_argument("data_repo", type=Path, help="checkout of resslab-hub-data")
    parser.add_argument("--base", default="origin/main", help="git ref of the repo")
    args = parser.parse_args(argv)

    delivery = args.delivery.resolve()
    target = args.data_repo.resolve() / FOLDER
    base = Base(args.data_repo.resolve(), args.base)
    try:
        headers, rows = import_main_table(delivery, base)
        fields, entries = import_dictionary(delivery, base, headers)
        profile_types = {
            row[headers.index("id")]: row[headers.index("profile_type")] for row in rows
        }
        write_table(target / MAIN_CSV, headers, rows)
        write_dictionary(target / DICTIONARY_CSV, fields, entries)
        empty = import_series(delivery, target, base, profile_types)
    except ImportError_ as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    built_up = sum(is_built_up(profile) for profile in profile_types.values())
    print(f"{len(rows)} records ({built_up} built-up), {len(headers)} columns")
    for relative in empty:
        kept = "the repo file stays" if base.read(relative) else "no file"
        print(f"left out the empty file {relative} ({kept})")

    problems = check_folder(target, base)
    for problem in problems:
        print(f"check failed: {problem}", file=sys.stderr)
    if problems:
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
