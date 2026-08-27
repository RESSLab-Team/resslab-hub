"""Tests for the CSV integrity validator.

Most of ``TableValidator`` checks a CSV against an ORM model's column
*metadata* (headers, nullability, declared SQL types), so those tests run
without PostgreSQL — the range-statistics query degrades to "no stats" when no
database is reachable. The range-warning tests at the bottom do need the test
database (they seed existing data to compare against).
"""

import csv
from pathlib import Path

from resslab_hub.data.uploader import Type, get_args_all, upload_one
from resslab_hub.data.validator import (
    PRIMARY_TYPE_MAP,
    PRIMARY_TYPES,
    CsvFileValidator,
    TableValidator,
    ValidationResult,
    validate_one_file,
)
from resslab_hub.models.database.brace import Brace
from resslab_hub.models.database.tensile_coupon import TensileCoupon
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


class TestTensileCoupons:
    """Tensile coupons validate like cyclic coupons: a record table plus one
    stress-strain file per specimen, keyed by ``<id>.csv`` (issue #274)."""

    def test_record_table_dispatches_to_the_model(self):
        validator = validate_one_file(Type.TENSILE_COUPON, "tensile_coupons.csv")
        assert isinstance(validator, TableValidator)
        assert validator.base_model is TensileCoupon

    def test_stress_strain_requires_the_uploader_columns(self):
        validator = validate_one_file(Type.TENSILE_COUPON_STRESS_STRAIN, "T1.csv")
        assert isinstance(validator, CsvFileValidator)
        assert validator.base_model is TensileCoupon
        # The columns the uploader reads (cf. ``upload_one``).
        assert set(validator.required_columns) == {"Sigma_true", "e_true"}
        assert validator.foreign_key_field == "id"

    def test_stress_strain_is_keyed_to_the_record_table(self):
        assert (
            PRIMARY_TYPE_MAP[Type.TENSILE_COUPON_STRESS_STRAIN] is Type.TENSILE_COUPON
        )
        assert Type.TENSILE_COUPON in PRIMARY_TYPES

    def test_every_uploaded_type_has_a_validator(self):
        # The contribution editor only unlocks a database once its whole
        # layout validates; a NotImplementedError here would surface as a 500.
        for arg_type, _ in get_args_all(Type.ALL_TENSILE_COUPON, ""):
            if arg_type in (Type.DICTIONARY, Type.README):
                continue
            validate_one_file(arg_type, "x.csv")

    def test_well_formed_record_is_valid(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(TableValidator, "_range_stats", lambda self: {})
        file_path = tmp_path / "tensile_coupons.csv"
        write_main_csv(file_path, TensileCoupon, [{"id": "batch1-bfl-A3"}])
        result = TableValidator(TensileCoupon).validate_one(str(file_path))
        assert result.is_valid(), result.errors


class TestRangeWarnings:
    """Warn when a value is far outside the range of existing data.

    Uses the throwaway test database: ``db_session`` guarantees empty tables at
    the start of each test, and seeding goes through the real uploader.
    """

    @staticmethod
    def _seed_braces(tmp_path: Path, count: int):
        # area spans 10..10+count-1; every other column gets fixture defaults.
        csv_path = tmp_path / "steel_braces.csv"
        write_main_csv(
            csv_path,
            Brace,
            [{"id": f"B{i}", "area": str(10 + i)} for i in range(count)],
        )
        upload_one(Type.BRACE, str(csv_path))

    @staticmethod
    def _validate_area(tmp_path: Path, area: str):
        file_path = tmp_path / "contribution.csv"
        write_main_csv(file_path, Brace, [{"id": "NEW", "area": area}])
        return TableValidator(Brace).validate_one(str(file_path))

    @staticmethod
    def _area_warnings(result):
        return [
            w for w in result.warnings if w.column == "area" and "range" in w.message
        ]

    def test_far_outlier_warns_but_stays_valid(self, tmp_path: Path, db_session):
        self._seed_braces(tmp_path, 20)  # area 10..29

        result = self._validate_area(tmp_path, "10000")

        warnings = self._area_warnings(result)
        assert len(warnings) == 1
        assert warnings[0].row == 1
        assert "10 to 29" in warnings[0].message
        assert "verify" in warnings[0].message
        assert result.is_valid()  # a warning, never an error

    def test_value_within_one_span_of_range_does_not_warn(
        self, tmp_path: Path, db_session
    ):
        self._seed_braces(tmp_path, 20)  # area 10..29, span 19 -> bounds [-9, 48]

        assert not self._area_warnings(self._validate_area(tmp_path, "45"))
        assert not self._area_warnings(self._validate_area(tmp_path, "25"))

    def test_too_little_existing_data_never_warns(self, tmp_path: Path, db_session):
        self._seed_braces(tmp_path, 19)  # below RANGE_MIN_COUNT

        assert not self._area_warnings(self._validate_area(tmp_path, "10000"))

    def test_empty_table_never_warns(self, tmp_path: Path, db_session):
        assert not self._area_warnings(self._validate_area(tmp_path, "10000"))


class TestPrimaryCsvIds:
    def test_parses_once_and_tracks_rewrites(self, tmp_path):
        from resslab_hub.data.validator import CsvFileValidator, primary_csv_ids

        primary = tmp_path / "steel_braces.csv"
        primary.write_text("id,area\nB1,10\nB2,12\n")
        validator = CsvFileValidator(None, [], "brace_id", str(primary))
        primary_csv_ids.cache_clear()

        assert validator._check_primary_csv("B1") is True
        assert validator._check_primary_csv("B9") is False
        # The second lookup came from the cache, not another scan of the file.
        assert primary_csv_ids.cache_info().misses == 1
        assert primary_csv_ids.cache_info().hits == 1

        # A rewritten primary (new size) is read again.
        primary.write_text("id,area\nB1,10\nB2,12\nB9,14\n")
        assert validator._check_primary_csv("B9") is True
        assert primary_csv_ids.cache_info().misses == 2

    def test_no_primary_means_no_match(self):
        from resslab_hub.data.validator import CsvFileValidator

        assert (
            CsvFileValidator(None, [], "brace_id", None)._check_primary_csv("B1")
            is False
        )
