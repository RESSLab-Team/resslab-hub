"""Pure-unit tests for the CSV integrity validator.

``TableValidator`` checks a CSV against an ORM model's column *metadata*
(headers, nullability, declared SQL types) -- it never opens a database
connection -- so these run without PostgreSQL.
"""

import csv
from pathlib import Path

from resslab_hub.data.validator import (
    TableValidator,
    ValidationResult,
)
from resslab_hub.models.database.brace import Brace
from tests.conftest import write_main_csv

BRACE_COLUMNS = [c.key for c in Brace.__table__.columns]


class TestValidationResult:
    def test_starts_valid_and_empty(self):
        result = ValidationResult("file.csv")
        assert result.is_valid() is True
        assert result.error_count == 0

    def test_add_error_marks_invalid_and_counts(self):
        result = ValidationResult("file.csv")
        result.add_error(1, "area", "abc", "Must be a number")
        assert result.is_valid() is False
        assert result.error_count == 1
        assert len(result.errors) == 1

    def test_warnings_do_not_invalidate(self):
        result = ValidationResult("file.csv")
        result.add_warning(1, "row", [], "Empty row detected")
        assert result.is_valid() is True
        assert len(result.warnings) == 1

    def test_str_lists_errors_and_warnings(self):
        result = ValidationResult("file.csv")
        result.add_error(2, "area", "abc", "Must be a number")
        text = str(result)
        assert "file.csv" in text
        assert "area" in text

    def test_file_path_defaults_to_filename(self):
        result = ValidationResult("file.csv")
        assert result.file_path == "file.csv"

    def test_file_path_is_retained(self):
        result = ValidationResult("file.csv", "/tmp/x/file.csv")
        assert result.file_path == "/tmp/x/file.csv"


class TestTableValidator:
    def test_well_formed_file_is_valid(self, tmp_path: Path):
        file_path = tmp_path / "braces.csv"
        write_main_csv(file_path, Brace, [{"id": "B1"}, {"id": "B2"}])

        result = TableValidator(Brace).validate_one(str(file_path))

        assert result.is_valid(), str(result)

    def test_missing_required_column_is_an_error(self, tmp_path: Path):
        file_path = tmp_path / "braces.csv"
        with open(file_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["id"])  # almost every column is missing
            writer.writerow(["B1"])

        result = TableValidator(Brace).validate_one(str(file_path))

        assert not result.is_valid()
        assert any("Missing required columns" in e.message for e in result.errors)

    def test_unexpected_column_is_a_warning(self, tmp_path: Path):
        file_path = tmp_path / "braces.csv"
        write_main_csv(file_path, Brace, [{"id": "B1"}])
        # Re-read and append a stray column to every line.
        lines = file_path.read_text(encoding="utf-8").splitlines()
        lines[0] += ",bogus_column"
        lines[1] += ",value"
        file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        result = TableValidator(Brace).validate_one(str(file_path))

        assert any("Unexpected columns" in w.message for w in result.warnings)

    def test_empty_row_is_warned_and_skipped(self, tmp_path: Path):
        file_path = tmp_path / "braces.csv"
        with open(file_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(BRACE_COLUMNS)
            writer.writerow(["" for _ in BRACE_COLUMNS])

        result = TableValidator(Brace).validate_one(str(file_path))

        assert any("Empty row" in w.message for w in result.warnings)

    def test_non_numeric_value_in_float_column_is_an_error(self, tmp_path: Path):
        file_path = tmp_path / "braces.csv"
        # 'area' is a Float column; a non-numeric value must be rejected.
        write_main_csv(file_path, Brace, [{"id": "B1", "area": "not-a-number"}])

        result = TableValidator(Brace).validate_one(str(file_path))

        assert not result.is_valid()
        assert any(e.column == "area" for e in result.errors)

    def test_non_integer_value_in_integer_column_is_an_error(self, tmp_path: Path):
        file_path = tmp_path / "braces.csv"
        # 'date' is a SmallInteger column on Brace.
        write_main_csv(file_path, Brace, [{"id": "B1", "date": "abc"}])

        result = TableValidator(Brace).validate_one(str(file_path))

        assert not result.is_valid()
        assert any(e.column == "date" for e in result.errors)

    def test_na_in_non_nullable_column_is_an_error(self, tmp_path: Path):
        file_path = tmp_path / "braces.csv"
        # 'investigator' is a non-nullable String column.
        write_main_csv(file_path, Brace, [{"id": "B1", "investigator": "NA"}])

        result = TableValidator(Brace).validate_one(str(file_path))

        assert not result.is_valid()
        assert any(e.column == "investigator" for e in result.errors)

    def test_row_numbering_is_one_based_excluding_header(self, tmp_path: Path):
        # The error must point at data row 2 (the second data row), proving the
        # header is excluded and numbering starts at 1. The frontend grid maps
        # server row N to grid row N-1, so this contract is load-bearing.
        file_path = tmp_path / "braces.csv"
        write_main_csv(
            file_path,
            Brace,
            [
                {"id": "B1", "area": "1.0"},
                {"id": "B2", "area": "not-a-number"},
            ],
        )

        result = TableValidator(Brace).validate_one(str(file_path))

        area_errors = [e for e in result.errors if e.column == "area"]
        assert area_errors, str(result)
        assert area_errors[0].row == 2

    def test_result_file_path_is_the_validated_file(self, tmp_path: Path):
        file_path = tmp_path / "braces.csv"
        write_main_csv(file_path, Brace, [{"id": "B1"}])

        result = TableValidator(Brace).validate_one(str(file_path))

        assert result.file_path.endswith("braces.csv")
