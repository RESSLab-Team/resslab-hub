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
    DuctileFractureTableValidator,
    EccentricBracedFrameTableValidator,
    ResidualStressTableValidator,
    TableValidator,
    ValidationResult,
    validate_one_file,
)
from resslab_hub.models.database.brace import Brace
from resslab_hub.models.database.ductile_fracture import DuctileFracture
from resslab_hub.models.database.eccentric_braced_frame import EccentricBracedFrame
from resslab_hub.models.database.material import Material
from resslab_hub.models.database.residual_stress import ResidualStress
from resslab_hub.models.database.tensile_coupon import TensileCoupon
from tests.conftest import write_main_csv, write_measurement_csv

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
        # The columns the uploader reads (cf. ``upload_one``). Tensile coupons
        # report engineering values, cyclic ones true values (issue #276).
        assert set(validator.required_columns) == {"Stress_eng", "strain_eng"}
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
        assert "Far outside" in warnings[0].message
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

    def test_nan_in_a_column_with_range_stats_only_gives_the_nan_warning(
        self, tmp_path: Path, db_session
    ):
        # #408: the range check raised on NaN and stopped the whole file.
        self._seed_braces(tmp_path, 20)  # area 10..29, so area has range stats
        file_path = tmp_path / "contribution.csv"
        write_main_csv(
            file_path,
            Brace,
            [{"id": "NAN", "area": "NaN"}, {"id": "FAR", "area": "10000"}],
        )

        result = TableValidator(Brace).validate_one(str(file_path))

        assert not any("Failed to process" in e.message for e in result.errors)
        nan_row = [w for w in result.warnings if w.row == 1 and w.column == "area"]
        assert len(nan_row) == 1
        assert "NaN is not accepted" in nan_row[0].message
        assert not [e for e in result.errors if e.row == 1 and e.column == "area"]
        # the next row is still checked
        far_row = [w for w in self._area_warnings(result) if w.row == 2]
        assert len(far_row) == 1

    def test_verified_ranges_leave_the_unverified_rows_out(
        self, tmp_path: Path, db_session
    ):
        # A verification checks rows already in the table (#253): an unverified
        # outlier must not stretch the range it is compared with.
        csv_path = tmp_path / "steel_braces.csv"
        rows = [
            {"id": f"B{i}", "area": str(10 + i), "data_curation_status": "verified"}
            for i in range(20)
        ]
        rows.append(
            {"id": "OUT", "area": "10000", "data_curation_status": "unverified"}
        )
        write_main_csv(csv_path, Brace, rows)
        upload_one(Type.BRACE, str(csv_path))
        file_path = tmp_path / "review.csv"
        write_main_csv(file_path, Brace, [{"id": "OUT", "area": "10000"}])

        every_row = TableValidator(Brace).validate_one(str(file_path))
        verified = TableValidator(Brace, verified_ranges=True).validate_one(
            str(file_path)
        )

        assert not self._area_warnings(every_row)
        assert "10 to 29" in self._area_warnings(verified)[0].message


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


# --- the rules the database READMEs state (issue #243) -----------------------
#
# Each class below covers one rule of the contributor READMEs
# (resslab-hub-data#48). The severity split is deliberate: an error is
# something that breaks the upload, a warning something a curator can still
# fix afterwards. Warnings never fail the data repository CI, which gates on
# ``valid`` only.


def brace_result(tmp_path: Path, row: dict, name: str = "steel_braces.csv"):
    """Validate a one-row braces CSV built from the fixture defaults."""
    file_path = write_main_csv(tmp_path / name, Brace, [{"id": "B1", **row}])
    return TableValidator(Brace).validate_one(str(file_path))


def messages(issues, column: str):
    return [issue.message for issue in issues if issue.column == column]


def all_messages(issues):
    return [issue.message for issue in issues]


class TestCurationStatus:
    """The review status (#253): the Hub sets it, contributors leave it out."""

    def test_a_file_without_the_column_is_valid(self, tmp_path: Path):
        file_path = write_main_csv(tmp_path / "steel_braces.csv", Brace, [{"id": "B1"}])
        # The defaults hold no comma, so a plain split is safe.
        lines = file_path.read_text(encoding="utf-8").splitlines()
        index = lines[0].split(",").index("data_curation_status")
        trimmed = [
            ",".join(cell for i, cell in enumerate(line.split(",")) if i != index)
            for line in lines
        ]
        file_path.write_text("\n".join(trimmed) + "\n", encoding="utf-8")

        result = TableValidator(Brace).validate_one(str(file_path))

        assert result.is_valid(), str(result)
        assert not any("Missing required" in m for m in all_messages(result.errors))

    def test_both_words_are_accepted(self, tmp_path: Path):
        for value in ("verified", "unverified"):
            result = brace_result(tmp_path, {"data_curation_status": value})
            assert messages(result.errors, "data_curation_status") == [], value

    def test_an_empty_cell_is_accepted(self, tmp_path: Path):
        result = brace_result(tmp_path, {"data_curation_status": ""})

        assert messages(result.errors, "data_curation_status") == []

    def test_another_word_is_an_error(self, tmp_path: Path):
        result = brace_result(tmp_path, {"data_curation_status": "checked"})

        assert not result.is_valid()
        assert any(
            "verified or unverified" in m
            for m in messages(result.errors, "data_curation_status")
        )


class TestMissingValues:
    """ "Leave no cell empty"; NA and NR are for nullable columns only."""

    def test_empty_cell_in_nullable_column_warns(self, tmp_path: Path):
        # 'l_1t' is a nullable String column.
        result = brace_result(tmp_path, {"l_1t": ""})

        assert result.is_valid()
        assert any("Empty cell" in m for m in messages(result.warnings, "l_1t"))

    def test_na_and_nr_in_nullable_column_are_silent(self, tmp_path: Path):
        for marker in ("NA", "NR", "na", "nr"):
            result = brace_result(tmp_path, {"l_1t": marker})
            assert messages(result.warnings, "l_1t") == [], marker
            assert messages(result.errors, "l_1t") == [], marker

    def test_empty_cell_in_mandatory_column_is_an_error(self, tmp_path: Path):
        result = brace_result(tmp_path, {"investigator": ""})

        assert not result.is_valid()
        assert any(
            "mandatory" in m.lower() for m in messages(result.errors, "investigator")
        )

    def test_nr_in_mandatory_number_is_an_error(self, tmp_path: Path):
        # The uploader turns NR into NULL and the whole file is skipped, so
        # this one has to stop the contributor. 'date' is a SmallInteger.
        result = brace_result(tmp_path, {"date": "NR"})

        assert not result.is_valid()
        assert any("mandatory" in m.lower() for m in messages(result.errors, "date"))

    def test_nr_in_mandatory_text_only_warns(self, tmp_path: Path):
        # A String column stores "Not reported" and uploads fine; the data
        # repository has hundreds of these already.
        result = brace_result(tmp_path, {"investigator": "NR"})

        assert result.is_valid()
        assert any(
            "not reported" in m.lower()
            for m in messages(result.warnings, "investigator")
        )

    def test_na_in_mandatory_text_is_an_error(self, tmp_path: Path):
        result = brace_result(tmp_path, {"investigator": "NA"})

        assert not result.is_valid()
        assert messages(result.errors, "investigator")

    def test_nan_counts_as_no_value(self, tmp_path: Path):
        assert any(
            "NaN" in m
            for m in messages(brace_result(tmp_path, {"l_1t": "NaN"}).warnings, "l_1t")
        )
        mandatory = brace_result(tmp_path, {"date": "NaN"})
        assert not mandatory.is_valid()
        assert any("NaN" in m for m in messages(mandatory.errors, "date"))


class TestNumbers:
    """ "Numeric values only, decimal point"; "a year alone is an integer"."""

    def test_decimal_comma_is_an_error(self, tmp_path: Path):
        result = brace_result(tmp_path, {"area": "1,5"})

        assert not result.is_valid()
        assert any("decimal point" in m for m in messages(result.errors, "area"))

    def test_decimal_point_is_accepted(self, tmp_path: Path):
        assert messages(brace_result(tmp_path, {"area": "1.5"}).errors, "area") == []

    def test_infinity_is_an_error(self, tmp_path: Path):
        result = brace_result(tmp_path, {"area": "inf"})

        assert not result.is_valid()
        assert any("real number" in m for m in messages(result.errors, "area"))

    def test_text_in_a_number_column_says_so(self, tmp_path: Path):
        result = brace_result(tmp_path, {"area": "abc"})

        assert any("Must be a number" in m for m in messages(result.errors, "area"))

    def test_year_with_decimals_warns_about_the_truncation(self, tmp_path: Path):
        # The upload stores int(Decimal(value)), so this loses the decimals
        # instead of failing: a warning, like the editor's own rule.
        result = brace_result(tmp_path, {"date": "2024.7"})

        assert result.is_valid()
        warnings = messages(result.warnings, "date")
        assert any("truncated" in m and "2024" in m for m in warnings)

    def test_year_written_with_a_trailing_zero_is_accepted(self, tmp_path: Path):
        assert brace_result(tmp_path, {"date": "2024.0"}).is_valid()


class TestDates:
    """ "Dates are dd.mm.yyyy". Only cyclic coupons have a Date column."""

    @staticmethod
    def _material(tmp_path: Path, value: str):
        file_path = write_main_csv(
            tmp_path / "steel_material.csv", Material, [{"id": "M1", "date": value}]
        )
        return TableValidator(Material).validate_one(str(file_path))

    def test_four_digit_year_is_accepted(self, tmp_path: Path):
        assert messages(self._material(tmp_path, "07.10.2020").errors, "date") == []

    def test_two_digit_year_is_an_error(self, tmp_path: Path):
        result = self._material(tmp_path, "07.10.20")

        assert not result.is_valid()
        assert any("dd.mm.yyyy" in m for m in messages(result.errors, "date"))

    def test_iso_date_is_an_error(self, tmp_path: Path):
        result = self._material(tmp_path, "2020-10-07")

        assert any("dd.mm.yyyy" in m for m in messages(result.errors, "date"))

    def test_impossible_day_is_an_error(self, tmp_path: Path):
        result = self._material(tmp_path, "32.10.2020")

        assert any("not a real date" in m for m in messages(result.errors, "date"))


class TestRowShapeAndHeaders:
    def test_row_with_extra_values_blames_the_decimal_comma(self, tmp_path: Path):
        file_path = tmp_path / "steel_braces.csv"
        write_main_csv(file_path, Brace, [{"id": "B1"}])
        lines = file_path.read_text(encoding="utf-8").splitlines()
        lines[1] += ",5"  # what an unquoted "1,5" does to a row
        file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        result = TableValidator(Brace).validate_one(str(file_path))

        assert not result.is_valid()
        assert any("decimal comma" in m for m in messages(result.errors, "row"))

    def test_trailing_comma_on_a_row_is_ignored(self, tmp_path: Path):
        file_path = tmp_path / "steel_braces.csv"
        write_main_csv(file_path, Brace, [{"id": "B1"}])
        lines = file_path.read_text(encoding="utf-8").splitlines()
        lines[1] += ","
        file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        assert TableValidator(Brace).validate_one(str(file_path)).is_valid()

    def test_semicolon_separator_says_so(self, tmp_path: Path):
        file_path = tmp_path / "steel_braces.csv"
        file_path.write_text("id;investigator\nB1;someone\n", encoding="utf-8")

        result = TableValidator(Brace).validate_one(str(file_path))

        assert not result.is_valid()
        assert any("semicolons" in m for m in messages(result.errors, "headers"))
        # The real cause is reported instead of every column being missing.
        assert not any("Missing required" in m for m in messages(result.errors, "head"))

    def test_column_without_a_name_is_warned(self, tmp_path: Path):
        file_path = tmp_path / "steel_braces.csv"
        write_main_csv(file_path, Brace, [{"id": "B1"}])
        lines = file_path.read_text(encoding="utf-8").splitlines()
        lines[0] += ","
        lines[1] += ","
        file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        result = TableValidator(Brace).validate_one(str(file_path))

        assert result.is_valid()
        assert any("has no name" in m for m in messages(result.warnings, "headers"))


class TestFileFormat:
    """ "Encoding UTF-8, comma separator, LF line endings, final newline"."""

    def test_clean_file_says_nothing(self, tmp_path: Path):
        result = brace_result(tmp_path, {})

        assert messages(result.warnings, "file") == []

    def test_windows_line_endings_warn(self, tmp_path: Path):
        file_path = tmp_path / "steel_braces.csv"
        write_main_csv(file_path, Brace, [{"id": "B1"}])
        text = file_path.read_text(encoding="utf-8")
        file_path.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))

        result = TableValidator(Brace).validate_one(str(file_path))

        assert result.is_valid()
        assert any("CRLF" in m for m in messages(result.warnings, "file"))

    def test_missing_final_newline_warns(self, tmp_path: Path):
        file_path = tmp_path / "steel_braces.csv"
        write_main_csv(file_path, Brace, [{"id": "B1"}])
        file_path.write_bytes(file_path.read_bytes().rstrip(b"\n"))

        result = TableValidator(Brace).validate_one(str(file_path))

        assert result.is_valid()
        assert any("newline" in m for m in messages(result.warnings, "file"))

    def test_non_utf8_file_warns(self, tmp_path: Path):
        file_path = tmp_path / "steel_braces.csv"
        write_main_csv(file_path, Brace, [{"id": "B1", "investigator": "Muller"}])
        raw = file_path.read_bytes().replace(b"Muller", "Müller".encode("latin-1"))
        file_path.write_bytes(raw)

        result = TableValidator(Brace).validate_one(str(file_path))

        assert any("not UTF-8" in m for m in messages(result.warnings, "file"))


class TestIdentifiers:
    def test_space_in_an_id_warns(self, tmp_path: Path):
        result = brace_result(tmp_path, {"id": "Wakabayashi_DIC 1-D1"})

        # Still a valid file name, so the naming convention is only a warning.
        assert result.is_valid()
        warnings = messages(result.warnings, "id")
        assert any("underscores, not spaces" in m for m in warnings)

    def test_id_that_cannot_be_a_file_name_is_an_error(self, tmp_path: Path):
        result = brace_result(tmp_path, {"id": "Fell/HSS1"})

        assert not result.is_valid()
        assert any("file name" in m for m in messages(result.errors, "id"))


class TestResponseFileRows:
    """The response files carry numbers only, one file per id."""

    @staticmethod
    def _validate(tmp_path: Path, rows, stem: str = "B1"):
        primary = write_main_csv(tmp_path / "steel_braces.csv", Brace, [{"id": "B1"}])
        folder = tmp_path / "force_displacement"
        folder.mkdir(exist_ok=True)
        curve = write_measurement_csv(
            folder / f"{stem}.csv", ["Displacement [mm]", "Force [kN]"], rows
        )
        validator = CsvFileValidator(
            Brace,
            ["Displacement [mm]", "Force [kN]"],
            "id",
            primary_csv_path=str(primary),
        )
        return validator.validate_one(str(curve))

    def test_numbers_are_accepted(self, tmp_path: Path):
        assert self._validate(tmp_path, [["0.0", "-1.5"], ["1.0", "2.5"]]).is_valid()

    def test_decimal_comma_is_an_error_naming_the_row(self, tmp_path: Path):
        result = self._validate(tmp_path, [["0.0", "1.0"], ["1,5", "2.0"]])

        assert not result.is_valid()
        assert any(m.startswith("Row 2:") for m in all_messages(result.errors))
        assert any("decimal point" in m for m in all_messages(result.errors))

    def test_nan_only_warns(self, tmp_path: Path):
        # Legacy files carry NaN where the instrument lost the reading.
        result = self._validate(tmp_path, [["0.0", "NaN"]])

        assert result.is_valid()
        assert any("NaN" in m for m in all_messages(result.warnings))

    def test_empty_cell_is_an_error(self, tmp_path: Path):
        result = self._validate(tmp_path, [["0.0", ""]])

        assert not result.is_valid()
        assert any("empty" in m for m in all_messages(result.errors))

    def test_a_repeated_problem_is_reported_once(self, tmp_path: Path):
        # One legacy file holds 187 000 NaN readings; one issue per row would
        # make the response unusable and the report unreadable.
        rows = [["0.0", "NaN"] for _ in range(50)]
        result = self._validate(tmp_path, rows)

        nan_warnings = [w for w in result.warnings if "NaN" in w.message]
        assert len(nan_warnings) == 1
        assert "47 more" in nan_warnings[0].message

    def test_empty_row_is_reported_as_such(self, tmp_path: Path):
        result = self._validate(tmp_path, [["0.0", "1.0"], ["", ""]])

        assert not result.is_valid()
        assert any("row is empty" in m for m in all_messages(result.errors))

    def test_file_named_after_an_unknown_id_is_rejected(self, tmp_path: Path):
        result = self._validate(tmp_path, [["0.0", "1.0"]], stem="B9")

        assert not result.is_valid()
        assert any("not found" in m for m in all_messages(result.errors))


class TestResidualStressFlanges:
    """``flange_nr_data`` must match the presence of a second flange file."""

    @staticmethod
    def _validate(tmp_path: Path, declared: str, with_f2: bool):
        root = tmp_path / "residual_stresses"
        root.mkdir(exist_ok=True)
        if with_f2:
            folder = root / "Distributions" / "Distributions_F2"
            folder.mkdir(parents=True, exist_ok=True)
            write_measurement_csv(
                folder / "R1.csv", ["coordinate", "residual_stress"], [["0", "1"]]
            )
        file_path = write_main_csv(
            root / "residual_stresses.csv",
            ResidualStress,
            [{"id": "R1", "flange_nr_data": declared}],
        )
        return ResidualStressTableValidator(ResidualStress).validate_one(str(file_path))

    def test_two_flanges_with_the_file_is_quiet(self, tmp_path: Path):
        result = self._validate(tmp_path, "2", with_f2=True)
        assert messages(result.warnings, "flange_nr_data") == []

    def test_one_flange_without_the_file_is_quiet(self, tmp_path: Path):
        result = self._validate(tmp_path, "1", with_f2=False)
        assert messages(result.warnings, "flange_nr_data") == []

    def test_two_flanges_without_the_file_warns(self, tmp_path: Path):
        result = self._validate(tmp_path, "2", with_f2=False)

        assert result.is_valid()
        assert any(
            "no Distributions_F2" in m
            for m in messages(result.warnings, "flange_nr_data")
        )

    def test_one_flange_with_the_file_warns(self, tmp_path: Path):
        result = self._validate(tmp_path, "1", with_f2=True)

        assert any("Write 2" in m for m in messages(result.warnings, "flange_nr_data"))

    def test_other_counts_warn(self, tmp_path: Path):
        result = self._validate(tmp_path, "3", with_f2=False)

        assert any("1 or 2" in m for m in messages(result.warnings, "flange_nr_data"))


class TestDuctileFracture:
    @staticmethod
    def _validate(tmp_path: Path, row: dict):
        file_path = write_main_csv(
            tmp_path / "ductile_fracture.csv",
            DuctileFracture,
            [{"id": "D1", "has_sem": "NR", **row}],
        )
        return DuctileFractureTableValidator(DuctileFracture).validate_one(
            str(file_path)
        )

    def test_measured_dimensions_as_a_json_list_are_accepted(self, tmp_path: Path):
        result = self._validate(tmp_path, {"meas_notch_width": "[1.97, 1.94, 1.96]"})

        assert messages(result.warnings, "meas_notch_width") == []

    def test_a_single_number_warns(self, tmp_path: Path):
        result = self._validate(tmp_path, {"meas_notch_width": "2.4"})

        assert result.is_valid()
        assert any(
            "list of numbers" in m
            for m in messages(result.warnings, "meas_notch_width")
        )

    def test_a_list_missing_its_bracket_warns(self, tmp_path: Path):
        result = self._validate(tmp_path, {"meas_notch_width": "24.85, 24.87]"})

        assert any(
            "list of numbers" in m
            for m in messages(result.warnings, "meas_notch_width")
        )

    def test_loading_protocol_is_a_list_too(self, tmp_path: Path):
        assert (
            messages(
                self._validate(tmp_path, {"loading_protocol": "[0,2]"}).warnings,
                "loading_protocol",
            )
            == []
        )

    def test_nr_is_left_alone(self, tmp_path: Path):
        result = self._validate(tmp_path, {"meas_width_gp": "NR"})

        assert messages(result.warnings, "meas_width_gp") == []

    def test_has_sem_belongs_to_the_hub(self, tmp_path: Path):
        result = self._validate(tmp_path, {"has_sem": "yes"})

        assert result.is_valid()
        assert any("SEM images" in m for m in messages(result.warnings, "has_sem"))


class TestEccentricBracedFrames:
    """EBF ids are running integers and its files are named ``id<id>.csv``."""

    @staticmethod
    def _record(tmp_path: Path, specimen_id: str):
        return write_main_csv(
            tmp_path / "eccentric_braced_frames.csv",
            EccentricBracedFrame,
            [{"id": specimen_id, "url": "https://example.org"}],
        )

    def test_integer_id_is_accepted(self, tmp_path: Path):
        result = EccentricBracedFrameTableValidator(EccentricBracedFrame).validate_one(
            str(self._record(tmp_path, "74"))
        )

        assert messages(result.errors, "id") == []

    def test_name_shaped_id_is_an_error(self, tmp_path: Path):
        result = EccentricBracedFrameTableValidator(EccentricBracedFrame).validate_one(
            str(self._record(tmp_path, "Kasai_1986_S1"))
        )

        assert not result.is_valid()
        assert any("whole number" in m for m in messages(result.errors, "id"))

    def test_processed_file_is_matched_through_its_id_prefix(self, tmp_path: Path):
        primary = self._record(tmp_path, "74")
        folder = tmp_path / "processed_data"
        folder.mkdir()
        curve = write_measurement_csv(
            folder / "id74.csv", ["data_ind", "gamma_t", "V"], [["0", "0.01", "120"]]
        )
        validator = CsvFileValidator(
            EccentricBracedFrame,
            ["gamma_t", "V"],
            "id",
            primary_csv_path=str(primary),
            filename_prefix="id",
        )

        assert validator.validate_one(str(curve)).is_valid()

    def test_every_uploaded_type_has_a_validator(self):
        # EBF and ductile fracture used to raise NotImplementedError here,
        # which surfaced as a 500 and kept the quality step disabled for them.
        for top in (Type.ALL_ECCENTRIC_BRACED_FRAME, Type.ALL_DUCTILE_FRACTURE):
            for arg_type, _ in get_args_all(top, ""):
                if arg_type in (Type.DICTIONARY, Type.README):
                    continue
                validate_one_file(arg_type, "x.csv")


def test_validate_all_keeps_the_root_log_level(tmp_path):
    """A /validate call must not turn the API's root logger to DEBUG (#264 H2)."""
    import logging

    from resslab_hub.data.validator import validate_all

    root = logging.getLogger()
    before = root.level
    root.setLevel(logging.WARNING)
    try:
        validate_all(Type.BRACE, [str(tmp_path)], cpu=1)
        assert root.level == logging.WARNING
    finally:
        root.setLevel(before)
