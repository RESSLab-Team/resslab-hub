"""
Validator for csv data integrity
"""

import re
import traceback
from abc import ABC, abstractmethod
from csv import DictReader, reader
from datetime import datetime
from decimal import ROUND_DOWN, Decimal, InvalidOperation
from functools import lru_cache
from glob import iglob
from json import JSONDecodeError, loads
from logging import debug, error, getLogger, info
from multiprocessing import get_context
from os import path, stat
from typing import Any, FrozenSet, List, Optional, Tuple

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
    text,
)
from sqlalchemy.orm import Session

from resslab_hub.data.common import (
    ID_SPACE_RULE,
    SAFE_ID_PATTERN,
    SAFE_ID_RULE,
    detect_encoding,
    get_abs_path,
    get_file_encoding,
    is_empty_row,
)
from resslab_hub.data.count_flags import COUNT_FLAGS
from resslab_hub.data.curation_status import ALLOWED, STATUS_COLUMN, VERIFIED
from resslab_hub.data.uploader import (
    Type,
    get_args_all,
    get_safe_cpu_count,
    initializer,
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

engine = create_engine(url, echo=False)

DecimalFloat = Float(asdecimal=True)


class ValidationError:
    def __init__(self, row: int, column: str, value: Any, message: str):
        self.row = row
        self.column = column
        self.value = value
        self.message = message

    def __str__(self):
        return f"Row {self.row}: {self.column}='{self.value}' - {self.message}"


class ValidationResult:
    def __init__(self, filename: str, file_path: str = None):
        self.filename = filename
        # Absolute path of the validated file. The router derives the
        # archive-relative path from this so time-series kinds that share a
        # basename (e.g. every residual-stress ``<id>.csv``) stay distinct.
        self.file_path = file_path if file_path is not None else filename
        self.errors: List[ValidationError] = []
        self.error_count: Integer = 0
        self.warnings: List[ValidationError] = []

    def add_error(self, row: int, column: str, value: Any, message: str):
        self.errors.append(ValidationError(row, column, value, message))
        self.error_count += 1

    def add_warning(self, row: int, column: str, value: Any, message: str):
        self.warnings.append(ValidationError(row, column, value, message))

    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def __str__(self):
        result = [f"Validation results for {self.filename}:"]
        if self.errors:
            result.append("\nErrors:")
            result.extend(f"  - {error}" for error in self.errors)
        if self.warnings:
            result.append("\nWarnings:")
            result.extend(f"  - {warning}" for warning in self.warnings)
        if not self.errors and not self.warnings:
            result.append("✓ All checks passed")
        return "\n".join(result)


class Validator(ABC):
    """
    Abstract class for all validators
    """

    @abstractmethod
    def validate_one(self, file_path: str) -> ValidationResult:
        """
        Validate one file
        """


#: The markers every README allows in place of a value: ``NA`` (not
#: applicable), ``NR`` (not reported). ``NaN`` is not documented but shows up
#: in files exported from pandas, and the uploader turns it into NULL like the
#: other two, so the validator treats it as a missing value rather than as a
#: broken number.
MISSING_MARKERS = ("NA", "NR", "NAN")

#: Dates are ``dd.mm.yyyy``. ``strptime`` alone is too lax here: ``%Y`` happily
#: reads the ``20`` of ``07.10.20`` as the year 20, so the shape is checked
#: with a regular expression first and the calendar with ``strptime`` after.
DATE_PATTERN = re.compile(r"^\d{1,2}\.\d{1,2}\.\d{4}$")

DATE_RULE = "Dates are dd.mm.yyyy, for example 07.10.2020."


#: A broken response file repeats the same problem on every row (one legacy
#: file holds 187 000 NaN readings). Report the first few rows and then say how
#: many more, so the report stays readable and the response stays small.
ROW_ISSUE_SAMPLE = 3


def collect_row_issue(groups: dict, column: str, message: str, row: int):
    """Group a row-level issue by column and message, keeping a sample."""
    entry = groups.setdefault((column, message), {"rows": [], "count": 0})
    entry["count"] += 1
    if len(entry["rows"]) < ROW_ISSUE_SAMPLE:
        entry["rows"].append(row)


def report_row_issues(result: ValidationResult, groups: dict, warnings: set):
    """Turn the grouped row issues into at most one issue per group.

    The frontend shows a time-series message without its row number, so each
    message names its own rows.
    """
    for (column, message), entry in groups.items():
        rows = entry["rows"]
        listed = ", ".join(str(row) for row in rows)
        if entry["count"] == 1:
            text = f"Row {listed}: {message}"
        elif entry["count"] <= ROW_ISSUE_SAMPLE:
            text = f"Rows {listed}: {message}"
        else:
            text = f"Rows {listed} and {entry['count'] - len(rows)} more: {message}"
        add = result.add_warning if message in warnings else result.add_error
        add(rows[0], column, None, text)


def parse_number(value: str) -> Tuple[Optional[Decimal], Optional[str]]:
    """Read one numeric cell the way the READMEs describe it.

    Returns ``(number, None)`` or ``(None, message)``. The messages name the
    fix, because the contributor reads them in the quality step and has to know
    what to type instead.
    """
    text = value.strip()
    if "," in text:
        return None, (
            "Use a decimal point and no thousands separator: write 1234.5, "
            "not 1,234.5 or 1,5."
        )
    try:
        number = Decimal(text)
    except (InvalidOperation, ValueError):
        return None, "Must be a number."
    if not number.is_finite():
        return None, "Must be a real number: NaN and infinity cannot be stored."
    return number, None


def check_file_format(result: ValidationResult, raw: bytes) -> str:
    """Check the conventions every README states for every CSV.

    Encoding UTF-8, LF line endings, final newline. All three are warnings: an
    upload survives them, and the data repository has its own CI job for the
    line endings. Returns the encoding so the caller can read the file once.
    """
    encoding = detect_encoding(raw)
    if encoding != "utf-8-sig":
        result.add_warning(
            0,
            "file",
            result.filename,
            f"File is not UTF-8 (it looks like {encoding}). Save it as UTF-8.",
        )
    if b"\r\n" in raw:
        result.add_warning(
            0,
            "file",
            result.filename,
            "Windows line endings (CRLF). Save the file with LF.",
        )
    if raw and not raw.endswith(b"\n"):
        result.add_warning(
            0,
            "file",
            result.filename,
            "No newline at the end of the file.",
        )
    return encoding


def check_separator(result: ValidationResult, headers: List[str]) -> bool:
    """Refuse a file whose columns are separated by semicolons.

    A semicolon file parses as a single column holding the whole header line,
    so every column looks missing. Say the real cause instead. Returns True
    when the file is unusable.
    """
    if len(headers) == 1 and ";" in headers[0]:
        result.add_error(
            0,
            "headers",
            headers,
            "Columns separated by semicolons. Save the file with a comma as separator.",
        )
        return True
    return False


def check_empty_headers(result: ValidationResult, headers: List[str]):
    """Warn about a column with no name (a stray trailing comma)."""
    positions = [str(i + 1) for i, name in enumerate(headers) if not name.strip()]
    if positions:
        result.add_warning(
            0,
            "headers",
            headers,
            f"Column {', '.join(positions)} has no name (extra comma in the "
            f"header). It is ignored.",
        )


# A range warning needs at least this many existing values before "the norm"
# means anything.
RANGE_MIN_COUNT = 20


class TableValidator(Validator):
    """
    Validator for table data (csv files with headers matching table columns)
    """

    def __init__(
        self,
        base_model: Any,
        id_column_key: str = "id",
        check_duplicate_ids: bool = False,
        verified_ranges: bool = False,
    ):
        self.base_model = base_model
        self.id_column_key = id_column_key
        # Opt-in (contribution checks only): the data-repo CI validates the
        # full repo CSVs, whose ids are all already in the database — flagging
        # those as duplicates would make that CI permanently red.
        self.check_duplicate_ids = check_duplicate_ids
        # The range warnings compare with verified rows only (#253). For a
        # verification: the unverified rows under review are in the table, so
        # an outlier would set the range itself and never be flagged.
        self.verified_ranges = verified_ranges

    def _existing_ids(self) -> set:
        """Ids already in the table; empty when the database is unreachable."""
        id_column = self.base_model.__table__.c[self.id_column_key]
        try:
            with Session(engine) as session:
                return {row[0] for row in session.execute(select(id_column))}
        except Exception:
            return set()

    def _range_stats(self) -> dict:
        """Per-column (count, min, max) over existing data, one query per file.

        Returns {} when the database is unreachable, keeping this validator
        usable without a database (header/type checks still run).
        """
        numeric_columns = [
            column
            for column in self.base_model.__table__.c
            if isinstance(column.type, (Integer, Numeric))
        ]
        if not numeric_columns:
            return {}
        aggregates = []
        for column in numeric_columns:
            aggregates.extend([func.count(column), func.min(column), func.max(column)])
        query = select(*aggregates)
        status = self.base_model.__table__.c.get(STATUS_COLUMN)
        if self.verified_ranges and status is not None:
            query = query.where(status == VERIFIED)
        try:
            with Session(engine) as session:
                row = session.execute(query).one()
        except Exception:
            return {}
        return {
            column.key: (row[i * 3], row[i * 3 + 1], row[i * 3 + 2])
            for i, column in enumerate(numeric_columns)
            if row[i * 3] >= RANGE_MIN_COUNT
        }

    @staticmethod
    def _check_range(
        result: ValidationResult, row: int, column_name: str, value: str, stats: dict
    ):
        """Warn when a value is far outside the range of existing data.

        The value is not necessarily wrong — the warning asks the contributor
        to double-check it. "Far outside" = beyond one full span of the
        observed [min, max] on either side.
        """
        if column_name not in stats:
            return
        try:
            number = Decimal(value)
        except (InvalidOperation, ValueError):
            return
        _, minimum, maximum = stats[column_name]
        # The driver returns Decimal for Numeric columns but float/int for the
        # others; normalize so the arithmetic below never mixes float with
        # Decimal (e.g. an all-zero Float column made `minimum - span` raise).
        minimum = Decimal(str(minimum))
        maximum = Decimal(str(maximum))
        span = maximum - minimum
        if span == 0:
            span = abs(maximum) or Decimal(1)
        if number < minimum - span or number > maximum + span:

            def plain(bound) -> str:
                return format(Decimal(bound).normalize(), "f")

            result.add_warning(
                row,
                column_name,
                value,
                f"Far outside the existing range "
                f"({plain(minimum)} to {plain(maximum)}).",
            )

    def validate_one(self, file_path: str) -> ValidationResult:
        file_path = get_abs_path(file_path)
        result = ValidationResult(path.basename(file_path), file_path)
        # Where the main CSV sits, so a row rule can look for a companion file
        # next to it (cf. ``ResidualStressTableValidator``).
        self.file_dir = path.dirname(file_path)
        range_stats = self._range_stats()
        existing_ids = self._existing_ids() if self.check_duplicate_ids else set()
        seen_ids: set = set()

        try:
            with open(file_path, "rb") as handle:
                raw = handle.read()
            encoding = check_file_format(result, raw)
            with open(file_path, encoding=encoding) as file:
                csv_reader = reader(file, strict=True)
                headers = next(csv_reader)

                # A semicolon file parses as one giant column: say that,
                # instead of listing every column as missing.
                if check_separator(result, headers):
                    return result
                check_empty_headers(result, headers)

                debug(f"Validating headers for {path.basename(file_path)}")
                # Validate headers. Derived *_count flags are physical columns
                # on the model but have no CSV header (recomputed at upload),
                # so they are never required from a contributed file.
                expected_columns = {
                    col.key for col in self.base_model.__table__.c
                } - set(COUNT_FLAGS.get(self.base_model, {}))

                debug(f"Expected columns: {expected_columns}")
                debug(f"Found columns: {headers}")

                # The review status is set by the Hub, not by the
                # contributor: accepted when present, never required.
                missing_columns = expected_columns - {STATUS_COLUMN} - set(headers)
                # An unnamed column already has its own warning above.
                unexpected_columns = {
                    name for name in headers if name.strip()
                } - expected_columns

                if missing_columns:
                    error(f"Missing columns: {missing_columns}")
                    result.add_error(
                        0,
                        "headers",
                        headers,
                        f"Missing required columns: {', '.join(missing_columns)}",
                    )

                if unexpected_columns:
                    error(f"Unexpected columns: {unexpected_columns}")
                    result.add_warning(
                        0,
                        "headers",
                        headers,
                        f"Unexpected columns: {', '.join(unexpected_columns)}",
                    )

                # Validate rows
                for row_num, row in enumerate(csv_reader, start=1):
                    if is_empty_row(row):
                        result.add_warning(row_num, "row", row, "Empty row detected")
                        continue
                    # Add check for incomplete rows
                    if len(row) < len(headers):
                        result.add_error(
                            row_num,
                            "row",
                            row,
                            f"Fewer values ({len(row)}) than headers ({len(headers)}).",
                        )
                        continue
                    # More values than headers is almost always a decimal comma
                    # inside an unquoted cell, which splits one value in two.
                    extra = [value for value in row[len(headers) :] if value.strip()]
                    if extra:
                        result.add_error(
                            row_num,
                            "row",
                            row,
                            f"More values ({len(row)}) than headers ({len(headers)}). "
                            f"A decimal comma splits a row: use a decimal point.",
                        )
                        continue

                    values = {}
                    for col_idx, value in enumerate(row):
                        debug(f"Validating row {row_num}, column {col_idx}: {value}")
                        if col_idx >= len(headers):
                            break

                        column_name = headers[col_idx]
                        values[column_name] = value
                        if column_name not in expected_columns:
                            continue
                        if column_name == STATUS_COLUMN:
                            self._check_status(result, row_num, value)
                            continue

                        column = self.base_model.__table__.c[column_name]
                        self._validate_field(result, row_num, column, value)
                        self._check_range(
                            result, row_num, column_name, value, range_stats
                        )
                        if column_name != self.id_column_key or not value.strip():
                            continue
                        specimen_id = value.strip()
                        self._check_id_form(
                            result, row_num, column_name, value, specimen_id
                        )
                        if self.check_duplicate_ids:
                            if specimen_id in existing_ids:
                                result.add_error(
                                    row_num,
                                    column_name,
                                    value,
                                    f"Specimen id '{specimen_id}' already "
                                    f"exists in the database.",
                                )
                            elif specimen_id in seen_ids:
                                result.add_error(
                                    row_num,
                                    column_name,
                                    value,
                                    f"Specimen id '{specimen_id}' appears more "
                                    f"than once in this contribution.",
                                )
                            seen_ids.add(specimen_id)

                    self._validate_row(result, row_num, values)

        except Exception as e:
            result.add_error(0, "file", file_path, f"Failed to process file: {str(e)}")

        return result

    def _check_id_form(
        self,
        result: ValidationResult,
        row: int,
        column_name: str,
        value: Any,
        specimen_id: str,
    ):
        """The id names the time-series file and ends up as a path in the data
        repository: refuse anything that cannot be a file name, here where the
        contributor sees it on the cell, rather than at submission. A space is
        a file name away from a problem, so it is only a warning."""
        if not SAFE_ID_PATTERN.fullmatch(specimen_id):
            result.add_error(
                row,
                column_name,
                value,
                f"Specimen id '{specimen_id}' cannot be used as "
                f"a file name: {SAFE_ID_RULE}.",
            )
        elif " " in specimen_id:
            result.add_warning(
                row,
                column_name,
                value,
                f"Specimen id '{specimen_id}' contains a space. {ID_SPACE_RULE}",
            )

    def _validate_row(self, result: ValidationResult, row: int, values: dict):
        """Rules that need more than one cell of the row. No-op by default."""

    def _check_status(self, result: ValidationResult, row: int, value: str):
        """The review status, when the file carries it: one of ALLOWED. An
        empty cell is fine, the upload reads it as unverified."""
        text = (value or "").strip()
        if text and text not in ALLOWED:
            result.add_error(
                row,
                STATUS_COLUMN,
                value,
                f"Must be {' or '.join(ALLOWED)}. The Hub sets this column, "
                f"you can leave it out.",
            )

    def _check_missing(
        self, result: ValidationResult, row: int, column: Any, value: str
    ) -> bool:
        """Apply the "leave no cell empty" rule of every README.

        ``NA`` (not applicable) and ``NR`` (not reported) are accepted in a
        nullable column. In a mandatory column they become NULL at upload and
        the whole file is skipped, except for text columns where they are
        stored as words. Returns True when the cell holds no value, so the
        caller skips the type checks.
        """
        text = (value or "").strip()
        marker = text.upper()
        if text and marker not in MISSING_MARKERS:
            return False

        is_text = isinstance(column.type, String)

        if not text:
            if column.nullable:
                result.add_warning(
                    row,
                    column.key,
                    value,
                    "Empty cell. Write NA (not applicable) or NR (not reported).",
                )
            else:
                result.add_error(
                    row,
                    column.key,
                    value,
                    "Mandatory, and the cell is empty.",
                )
            return True

        if marker == "NAN":
            if column.nullable:
                result.add_warning(
                    row,
                    column.key,
                    value,
                    "NaN is not accepted. Write NA (not applicable) or NR "
                    "(not reported).",
                )
            else:
                result.add_error(
                    row,
                    column.key,
                    value,
                    "Mandatory, and NaN cannot be stored.",
                )
            return True

        if column.nullable:
            return True

        if is_text:
            if marker == "NR":
                result.add_warning(
                    row,
                    column.key,
                    value,
                    "Mandatory. NR means not reported: give the real value if "
                    "you have it.",
                )
            else:
                result.add_error(
                    row,
                    column.key,
                    value,
                    "Mandatory, so NA cannot be right.",
                )
            return True

        result.add_error(
            row,
            column.key,
            value,
            f"Mandatory. {marker} counts as no value.",
        )
        return True

    def _validate_field(
        self, result: ValidationResult, row: int, column: Any, value: str
    ):
        # cf analyzer.py for column type determination and reference for now
        try:
            if self._check_missing(result, row, column, value):
                return

            text = value.strip()

            # Validate based on column type
            if isinstance(column.type, String):
                return
            elif isinstance(column.type, Boolean):
                if text.lower() not in ("yes", "no"):
                    result.add_error(row, column.key, value, "Must be 'yes' or 'no'")
            elif isinstance(column.type, (SmallInteger, Integer, BigInteger)):
                number, message = parse_number(text)
                if message:
                    result.add_error(row, column.key, value, message)
                elif number != number.to_integral_value():
                    # The upload truncates (``int(Decimal(value))``), so this
                    # loses the decimals without failing: a warning, worded
                    # like the editor's own rule so both engines agree.
                    whole = number.to_integral_value(rounding=ROUND_DOWN)
                    result.add_warning(
                        row,
                        column.key,
                        value,
                        f"Will be truncated to a whole number ({whole}). "
                        f"Write the whole number.",
                    )
            elif isinstance(column.type, (Float, Numeric)):
                _, message = parse_number(text)
                if message:
                    result.add_error(row, column.key, value, message)
            elif isinstance(column.type, Date):
                if not DATE_PATTERN.match(text):
                    result.add_error(row, column.key, value, DATE_RULE)
                else:
                    try:
                        datetime.strptime(text, "%d.%m.%Y")
                    except ValueError:
                        result.add_error(
                            row,
                            column.key,
                            value,
                            f"This is not a real date. {DATE_RULE}",
                        )

        except Exception as e:
            print(
                f"Validation error missing type: {str(e)}"
                f"for column {column.key} with value {value}"
                f"and type {column.type}"
            )
            result.add_error(row, column.key, value, f"Validation error: {str(e)}")


@lru_cache(maxsize=32)
def primary_csv_ids(path: str, mtime_ns: int, size: int) -> FrozenSet[str]:
    """The ``id`` column of a primary CSV, parsed once per file.

    Every time-series file of an upload checks its foreign key against the
    same primary CSV; re-reading it per file made the cost of one request
    grow with (files x rows), which an unauthenticated ``/validate`` of a
    2000-member archive turns into gigabytes of decoding. The mtime and size
    in the key keep a rewritten file from hitting a stale entry.
    """
    encoding = get_file_encoding(path)
    with open(path, encoding=encoding) as file:
        return frozenset((row.get("id") or "") for row in DictReader(file)) - {""}


class CsvFileValidator(Validator):
    """
    Validator for CSV files with specific column requirements
    """

    def __init__(
        self,
        base_model: Any,
        required_columns: List[str],
        foreign_key_field: str,
        primary_csv_path: str = None,
        filename_prefix: str = "",
    ) -> None:
        self.base_model = base_model
        self.required_columns = required_columns
        self.foreign_key_field = foreign_key_field
        self.primary_csv_path = primary_csv_path
        # EBF names its files ``id74.csv`` for the record whose id is ``74``,
        # like the uploader does.
        self.filename_prefix = filename_prefix

    def _check_primary_csv(self, foreign_key: str) -> bool:
        """Check if the foreign key exists in the primary CSV being uploaded"""
        if not self.primary_csv_path:
            return False

        try:
            primary = get_abs_path(self.primary_csv_path)
            info = stat(primary)
            found = foreign_key in primary_csv_ids(
                primary, info.st_mtime_ns, info.st_size
            )
            if not found:
                error(f"No match found for foreign key: {foreign_key}")
            return found
        except Exception as e:
            error(f"Error checking primary CSV: {str(e)}")
            return False

    def _exists_in_db(self, foreign_key: str) -> bool:
        """Whether the record is already in the database.

        Split out of ``validate_one`` so the row rules can be tested without
        PostgreSQL; returns False when the database is unreachable, like the
        other database-backed checks of this module.
        """
        try:
            with Session(engine) as session:
                stmt = text(
                    f'SELECT 1 FROM "{self.base_model.__tablename__}" '
                    f"WHERE {self.foreign_key_field} = :id"
                )
                return session.execute(stmt, {"id": foreign_key}).first() is not None
        except Exception as e:
            error(f"Error checking the database: {str(e)}")
            return False

    def validate_one(self, file_path: str) -> ValidationResult:
        relative_path = file_path
        try:
            file_path = get_abs_path(file_path)
            relative_path = path.relpath(
                file_path, start=path.join(path.sep, *file_path.split(path.sep)[:7])
            )
            result = ValidationResult(path.basename(file_path), file_path)
            filename = path.splitext(path.basename(file_path))[0]
            foreign_key = filename.removeprefix(self.filename_prefix)

            with open(file_path, "rb") as handle:
                raw = handle.read()
            encoding = check_file_format(result, raw)

            with open(file_path, encoding=encoding) as file:
                csv_reader = DictReader(file, strict=True)
                headers = list(csv_reader.fieldnames or [])

                if check_separator(result, headers):
                    return result

                # Validate headers
                missing_columns = set(self.required_columns) - set(headers)
                if missing_columns:
                    result.add_error(
                        0,
                        "headers",
                        headers,
                        f"Missing required columns: {', '.join(missing_columns)}",
                    )
                    return result

                # Check if foreign key exists
                exists_in_db = self._exists_in_db(foreign_key)
                exists_in_primary = self._check_primary_csv(foreign_key)

                if self.primary_csv_path is None:
                    if not exists_in_db:
                        result.add_error(
                            0,
                            self.foreign_key_field,
                            foreign_key,
                            f"Foreign key '{foreign_key}' not found in "
                            f"database, no primary csv provided (cf "
                            f"{relative_path})",
                        )
                elif not exists_in_primary:
                    result.add_error(
                        0,
                        self.foreign_key_field,
                        foreign_key,
                        f"Foreign key '{foreign_key}' not found "
                        f"in primary CSV (cf {relative_path})",
                    )

                # Validate each row. Identical problems are grouped so a file
                # that repeats one on thousands of rows still reports once.
                empty_row_message = "the row is empty, remove it."
                nan_message = (
                    "NaN means no reading. Remove the row if the measurement "
                    "is missing."
                )
                groups: dict = {}
                for row_num, row in enumerate(csv_reader, start=1):
                    if not any((value or "").strip() for value in row.values()):
                        collect_row_issue(groups, "row", empty_row_message, row_num)
                        continue
                    for col_name in self.required_columns:
                        # we don't validate against model definition because
                        # it may contain additional columns that are not required
                        # and it's always of type Numeric
                        value = row.get(col_name)
                        if value is None or value.strip() == "":
                            collect_row_issue(
                                groups, col_name, "required field is empty.", row_num
                            )
                            continue
                        if value.strip().upper() == "NAN":
                            # Postgres stores a float NaN, so the upload works;
                            # the contributor still has to know it is there.
                            collect_row_issue(groups, col_name, nan_message, row_num)
                            continue
                        _, message = parse_number(value)
                        if message:
                            collect_row_issue(groups, col_name, message, row_num)

                report_row_issues(result, groups, warnings={nan_message})
        except Exception as e:
            result = ValidationResult(path.basename(str(relative_path)), file_path)
            result.add_error(
                0, "file", relative_path, f"Failed to process file: {str(e)}"
            )

        return result


class ResidualStressTableValidator(TableValidator):
    """Residual stresses: ``flange_nr_data`` says how many flange
    distributions the record carries, so it must agree with the presence of a
    ``Distributions_F2`` file (README of ``residual_stresses/``)."""

    F2_DIRECTORY = path.join("Distributions", "Distributions_F2")

    def _validate_row(self, result: ValidationResult, row: int, values: dict):
        declared = (values.get("flange_nr_data") or "").strip()
        specimen_id = (values.get("id") or "").strip()
        if not declared or not specimen_id:
            return
        if declared.upper() in MISSING_MARKERS:
            return
        if declared not in ("1", "2"):
            result.add_warning(
                row,
                "flange_nr_data",
                declared,
                "Expected 1 or 2: the number of flange distributions provided.",
            )
            return
        has_file = path.isfile(
            path.join(self.file_dir, self.F2_DIRECTORY, f"{specimen_id}.csv")
        )
        if declared == "2" and not has_file:
            result.add_warning(
                row,
                "flange_nr_data",
                declared,
                "Two flange distributions are declared, but no "
                "Distributions_F2 file was attached for this record.",
            )
        elif declared == "1" and has_file:
            result.add_warning(
                row,
                "flange_nr_data",
                declared,
                "One flange distribution is declared, but a Distributions_F2 "
                "file was attached for this record. Write 2.",
            )


class DuctileFractureTableValidator(TableValidator):
    """Ductile fracture: measured dimensions and the loading protocol are
    written as JSON lists, and ``has_sem`` is maintained by the hub's SEM
    script (README of ``material/ductile_fracture/``)."""

    LIST_COLUMNS = ("loading_protocol",)

    def _validate_row(self, result: ValidationResult, row: int, values: dict):
        for name, value in values.items():
            if name != "has_sem":
                continue
            if (value or "").strip().lower() in ("yes", "no"):
                result.add_warning(
                    row,
                    name,
                    value,
                    "has_sem is set by the hub when the SEM images are "
                    "processed. Leave it NR in a contribution.",
                )

        for name, value in values.items():
            if name not in self.LIST_COLUMNS and not name.startswith("meas_"):
                continue
            text_value = (value or "").strip()
            if not text_value or text_value.upper() in MISSING_MARKERS:
                continue
            if not self._is_number_list(text_value):
                result.add_warning(
                    row,
                    name,
                    value,
                    "Expected a list of numbers between square brackets, for "
                    "example [7.99, 7.99, 8.01].",
                )

    @staticmethod
    def _is_number_list(value: str) -> bool:
        try:
            parsed = loads(value)
        except (JSONDecodeError, ValueError):
            return False
        return isinstance(parsed, list) and all(
            isinstance(item, (int, float)) and not isinstance(item, bool)
            for item in parsed
        )


class EccentricBracedFrameTableValidator(TableValidator):
    """EBF ids are integers assigned in order of insertion, not names
    (README of ``eccentric_braced_frames/``)."""

    def _check_id_form(
        self,
        result: ValidationResult,
        row: int,
        column_name: str,
        value: Any,
        specimen_id: str,
    ):
        if not specimen_id.isdigit():
            result.add_error(
                row,
                column_name,
                value,
                f"Id '{specimen_id}' must be a whole number: EBF records are "
                f"numbered in order of insertion, take the next free number.",
            )


def validate_one_file(input_type: Type, filename: str) -> Validator:
    """
    Validate a single file based on its type
    """
    info(f"Validating {filename} as {input_type}")

    match input_type:
        case Type.BRACE:
            validator = TableValidator(Brace)
        case Type.COLUMN:
            validator = TableValidator(ColumnEntity)
        case Type.CONNECTION:
            validator = TableValidator(Connection)
        case Type.MATERIAL:
            validator = TableValidator(Material)
        case Type.RESIDUAL_STRESS:
            validator = ResidualStressTableValidator(ResidualStress)
        case Type.HSS_COLUMN:
            validator = TableValidator(HSSColumn)
        case Type.ECCENTRIC_BRACED_FRAME:
            validator = EccentricBracedFrameTableValidator(EccentricBracedFrame)
        case Type.DUCTILE_FRACTURE:
            validator = DuctileFractureTableValidator(DuctileFracture)
        case Type.BRACE_DISPLACEMENT:
            validator = CsvFileValidator(
                Brace,
                ["Displacement [mm]", "Force [kN]"],
                "id",  # id column in brace table
            )
        case Type.COLUMN_AXIAL_SHORTENING:
            validator = CsvFileValidator(
                ColumnEntity,
                ["Chord Rotation [rads]", "Axial Shortening [mm]"],
                "id",
            )
        case Type.COLUMN_MOMENT_STRONG:
            validator = CsvFileValidator(
                ColumnEntity,
                ["Chord Rotation [rads]", "Moment [kN-mm]"],
                "id",
            )
        case Type.COLUMN_MOMENT_WEAK:
            validator = CsvFileValidator(
                ColumnEntity,
                ["Chord Rotation [rads]", "Moment [kN-mm]"],
                "id",
            )
        case Type.CONNECTION_BEAM:
            validator = CsvFileValidator(
                Connection, ["Chord Rotation [rads]", "Moment [kN-mm]"], "id"
            )
        case Type.CONNECTION_BEAM_WEST:
            validator = CsvFileValidator(
                Connection,
                [
                    "Chord Rotation [rads]",
                    "Moment [kN-mm]",
                ],
                "id",
            )
        case Type.CONNECTION_GLOBAL:
            validator = CsvFileValidator(
                Connection,
                [
                    "Total story drift angle (rad)",
                    "Force in the actuator (kN)",
                ],
                "id",
            )
        case Type.CONNECTION_GLOBAL_WEST:
            validator = CsvFileValidator(
                Connection,
                [
                    "Total story drift angle (rad)",
                    "Force in the actuator (kN)",
                ],
                "id",
            )
        case Type.CONNECTION_PANEL_ZONE:
            validator = CsvFileValidator(
                Connection,
                [
                    "panel zone shear distortion (rad)",
                    "panel zone shear force (kN)",
                ],
                "id",
            )
        case Type.MATERIAL_STRESS_STRAIN:
            validator = CsvFileValidator(Material, ["Sigma_true", "e_true"], "id")
        case Type.TENSILE_COUPON:
            validator = TableValidator(TensileCoupon)
        case Type.TENSILE_COUPON_STRESS_STRAIN:
            # Tensile coupons report engineering values, cyclic ones true
            # values (resslab-hub#276).
            validator = CsvFileValidator(
                TensileCoupon, ["Stress_eng", "strain_eng"], "id"
            )
        case Type.RESIDUAL_STRESS_DISTRIBUTION_F1:
            validator = CsvFileValidator(
                ResidualStress,
                ["coordinate", "residual_stress"],
                "id",
            )
        case Type.RESIDUAL_STRESS_DISTRIBUTION_F2:
            validator = CsvFileValidator(
                ResidualStress,
                ["coordinate", "residual_stress"],
                "id",
            )
        case Type.RESIDUAL_STRESS_DISTRIBUTION_W1:
            validator = CsvFileValidator(
                ResidualStress,
                ["coordinate", "residual_stress"],
                "id",
            )
        case Type.RESIDUAL_STRESS_QP_COEFFICIENT:
            validator = CsvFileValidator(
                ResidualStress,
                ["qp_coefficient"],
                "id",
            )
        case Type.HSS_COLUMN_MOMENT_ROTATION:
            validator = CsvFileValidator(
                HSSColumn,
                ["rotation (rad)", "moment (kN.m)"],
                "id",
            )
        case Type.ECCENTRIC_BRACED_FRAME_SHEAR_LINK_ANGLE:
            validator = CsvFileValidator(
                EccentricBracedFrame,
                ["gamma_t", "V"],
                "id",
                # The file of record 74 is ``processed_data/id74.csv``.
                filename_prefix="id",
            )
        case Type.DUCTILE_FRACTURE_FORCE_ELONGATION:
            validator = CsvFileValidator(
                DuctileFracture,
                ["Elongation [mm]", "Load [kN]"],
                "id",
            )
        case Type.DUCTILE_FRACTURE_FORCE_ELONGATION_SIMULATION:
            validator = CsvFileValidator(
                DuctileFracture,
                ["Elongation [mm]", "Load [kN]"],
                "id",
            )
        case Type.DUCTILE_FRACTURE_FORCE_RADIAL:
            validator = CsvFileValidator(
                DuctileFracture,
                ["Radial elongation [mm]", "Load [kN]"],
                "id",
            )
        case Type.DUCTILE_FRACTURE_FORCE_RADIAL_SIMULATION:
            validator = CsvFileValidator(
                DuctileFracture,
                ["Radial elongation [mm]", "Load [kN]"],
                "id",
            )
        case Type.DUCTILE_FRACTURE_EPEQ_SIMULATION:
            validator = CsvFileValidator(
                DuctileFracture,
                ["Elongation [mm]", "Equivalent plastic strain"],
                "id",
            )
        case Type.DUCTILE_FRACTURE_LODE_SIMULATION:
            validator = CsvFileValidator(
                DuctileFracture,
                ["Elongation [mm]", "Lode angle"],
                "id",
            )
        case Type.DUCTILE_FRACTURE_TRIAX_SIMULATION:
            validator = CsvFileValidator(
                DuctileFracture,
                ["Elongation [mm]", "Triaxiality"],
                "id",
            )
        case _:
            raise NotImplementedError(f"Unknown type {input_type}")

    return validator


# Map subsidiary types to their primary types
PRIMARY_TYPE_MAP = {
    Type.BRACE_DISPLACEMENT: Type.BRACE,
    Type.COLUMN_AXIAL_SHORTENING: Type.COLUMN,
    Type.COLUMN_MOMENT_STRONG: Type.COLUMN,
    Type.COLUMN_MOMENT_WEAK: Type.COLUMN,
    Type.CONNECTION_BEAM: Type.CONNECTION,
    Type.CONNECTION_BEAM_WEST: Type.CONNECTION,
    Type.CONNECTION_GLOBAL: Type.CONNECTION,
    Type.CONNECTION_GLOBAL_WEST: Type.CONNECTION,
    Type.CONNECTION_PANEL_ZONE: Type.CONNECTION,
    Type.MATERIAL_STRESS_STRAIN: Type.MATERIAL,
    Type.RESIDUAL_STRESS_DISTRIBUTION_F1: Type.RESIDUAL_STRESS,
    Type.RESIDUAL_STRESS_DISTRIBUTION_F2: Type.RESIDUAL_STRESS,
    Type.RESIDUAL_STRESS_DISTRIBUTION_W1: Type.RESIDUAL_STRESS,
    Type.RESIDUAL_STRESS_QP_COEFFICIENT: Type.RESIDUAL_STRESS,
    Type.HSS_COLUMN_MOMENT_ROTATION: Type.HSS_COLUMN,
    Type.TENSILE_COUPON_STRESS_STRAIN: Type.TENSILE_COUPON,
    Type.ECCENTRIC_BRACED_FRAME_SHEAR_LINK_ANGLE: Type.ECCENTRIC_BRACED_FRAME,
    Type.DUCTILE_FRACTURE_FORCE_ELONGATION: Type.DUCTILE_FRACTURE,
    Type.DUCTILE_FRACTURE_FORCE_ELONGATION_SIMULATION: Type.DUCTILE_FRACTURE,
    Type.DUCTILE_FRACTURE_FORCE_RADIAL: Type.DUCTILE_FRACTURE,
    Type.DUCTILE_FRACTURE_FORCE_RADIAL_SIMULATION: Type.DUCTILE_FRACTURE,
    Type.DUCTILE_FRACTURE_EPEQ_SIMULATION: Type.DUCTILE_FRACTURE,
    Type.DUCTILE_FRACTURE_LODE_SIMULATION: Type.DUCTILE_FRACTURE,
    Type.DUCTILE_FRACTURE_TRIAX_SIMULATION: Type.DUCTILE_FRACTURE,
}

#: The record-per-experiment tables; every other validated type is a
#: time-series file keyed to one of these through ``PRIMARY_TYPE_MAP``.
PRIMARY_TYPES = frozenset(PRIMARY_TYPE_MAP.values())


def validate_with_primary(
    input_type: Type,
    filename: str,
    primary_csv_paths: dict = None,
    check_duplicate_ids: bool = False,
    verified_ranges: bool = False,
) -> ValidationResult:
    """Helper function to create validator with appropriate primary CSV
    Args:
        input_type: The type of input file being validated
        filename: Path to the file being validated
    Returns:
        ValidationResult containing validation outcome
    """
    """Helper function to create validator with appropriate primary CSV"""
    try:
        validator = validate_one_file(input_type, filename)
        if isinstance(validator, TableValidator):
            validator.check_duplicate_ids = check_duplicate_ids
            validator.verified_ranges = verified_ranges
        if isinstance(validator, CsvFileValidator):
            primary_type = PRIMARY_TYPE_MAP.get(input_type)
            if primary_type and primary_csv_paths:
                primary_csv_path = primary_csv_paths.get(primary_type)
                validator.primary_csv_path = primary_csv_path
        return validator.validate_one(filename)
    except Exception as e:
        error(f"Error in validate_with_primary: {str(e)}")
        error(f"Traceback: {traceback.format_exc()}")
        raise


# A single file validates in milliseconds, but the ``spawn`` pool re-imports the
# whole app (~100 MB, ~0.4 s) in every worker. That overhead only pays off for
# the bulk validation path (thousands of files); below this many tasks -- e.g. a
# single contribution's record plus its handful of time-series files -- running
# inline is both faster and far lighter on memory (no per-core interpreter fan-out
# that OOM-kills a memory-capped pod).
_PARALLEL_MIN_TASKS = 32


def _run_validations(
    tasks,
    primary_csv_paths,
    cpu,
    log_level,
    log_format,
    check_duplicate_ids=False,
    verified_ranges=False,
) -> List[ValidationResult]:
    """Validate a batch of files, using a process pool only for bulk inputs."""
    if not tasks:
        return []
    workers = min(cpu, len(tasks))
    if workers <= 1 or len(tasks) < _PARALLEL_MIN_TASKS:
        return [
            validate_with_primary(
                t, f, primary_csv_paths, check_duplicate_ids, verified_ranges
            )
            for t, f in tasks
        ]
    with get_context("spawn").Pool(
        workers,
        initializer=initializer,
        initargs=(log_level, log_format),
    ) as pool:
        return pool.starmap(
            validate_with_primary,
            [
                (t, f, primary_csv_paths, check_duplicate_ids, verified_ranges)
                for t, f in tasks
            ],
        )


def validate_all(
    input_type: Type,
    filenames: List[str],
    cpu=None,
    check_duplicate_ids: bool = False,
    verified_ranges: bool = False,
) -> List[ValidationResult]:
    """
    Validate all files in parallel
    """
    if cpu is None:
        cpu = get_safe_cpu_count()

    info(f"Number of CPUs available: {cpu}")

    # Get current logging configuration to pass to workers. Don't change it:
    # the root logger is shared with the whole API process (#264 H2).
    current_log_level = getLogger().level
    root_logger = getLogger()
    current_log_format = None
    if root_logger.handlers and hasattr(root_logger.handlers[0], "formatter"):
        if root_logger.handlers[0].formatter:
            current_log_format = root_logger.handlers[0].formatter._fmt

    wildcard_args = [
        arg for filename in filenames for arg in get_args_all(input_type, filename)
    ]
    args = [
        (arg[0], filename)
        for arg in wildcard_args
        for filename in iglob(arg[1])
        # Dictionary CSVs and READMEs are upload metadata, not contributed
        # data: archives from the data repo contain them, but there is nothing
        # to validate.
        if arg[0] not in (Type.DICTIONARY, Type.README)
    ]

    # Split into primary and subsidiary types
    primary_types = [arg for arg in args if arg[0] in PRIMARY_TYPES]
    subsidiary_types = [arg for arg in args if arg not in primary_types]
    info(
        f"Found {len(primary_types)} primary types"
        f"and {len(subsidiary_types)} subsidiary types"
    )

    # Create mapping of primary CSV paths
    primary_csv_paths = {
        primary: next((f for t, f in primary_types if t == primary), None)
        for primary in PRIMARY_TYPES
    }

    results = []

    # First validate primary files
    if primary_types:
        debug(f"Validating primary types: {[t.name for t, _ in primary_types]}")
        try:
            results.extend(
                _run_validations(
                    primary_types,
                    primary_csv_paths,
                    cpu,
                    current_log_level,
                    current_log_format,
                    check_duplicate_ids,
                    verified_ranges,
                )
            )
        except Exception as e:
            error(f"Error in validate_all: {str(e)}")
            error(f"Traceback: {traceback.format_exc()}")
        # Check if all primary validations passed before proceeding
        # primary_errors = any(not result.is_valid() for result in primary_results)
        # if primary_errors:
        #     error("Primary file validation failed. Skipping subsidiary files.")
        #     return results

    # Then validate subsidiary files
    if subsidiary_types:
        debug(f"Validating subsidiary types: {[t.name for t, _ in subsidiary_types]}")
        results.extend(
            _run_validations(
                subsidiary_types,
                primary_csv_paths,
                cpu,
                current_log_level,
                current_log_format,
            )
        )

    # Log results
    for result in results:
        if result.is_valid():
            info(str(result))
        else:
            error(str(result))

    return results
