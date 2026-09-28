"""Pure-unit tests for the section-table CSV transformer (no database)."""

import csv
from decimal import Decimal
from pathlib import Path

from data.csv_transformer import Mapping, from_number, transform


class TestFromNumber:
    def test_parses_a_plain_string(self):
        assert from_number("25.4") == Decimal("25.4")

    def test_strips_thousands_apostrophes(self):
        # Swiss/Japanese section tables group thousands with apostrophes.
        assert from_number("1'234.5") == Decimal("1234.5")

    def test_normalizes_trailing_zeros(self):
        assert str(from_number("1.500")) == "1.5"

    def test_accepts_a_decimal_input(self):
        assert from_number(Decimal("3.0")) == Decimal("3")


class TestTransform:
    def test_writes_header_and_mapped_rows(self, tmp_path: Path):
        input_path = tmp_path / "in.csv"
        with open(input_path, "w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["section", "width"])
            writer.writerow(["IPE200", "1'234.5"])

        output_path = tmp_path / "out.csv"
        mappings = [
            Mapping("id", lambda row: row["section"]),
            Mapping("bf", lambda row: from_number(row["width"])),
        ]

        transform(str(input_path), str(output_path), mappings)

        with open(output_path, newline="") as handle:
            rows = list(csv.reader(handle))
        assert rows[0] == ["id", "bf"]
        assert rows[1] == ["IPE200", "1234.5"]

    def test_skips_fully_blank_rows(self, tmp_path: Path):
        input_path = tmp_path / "in.csv"
        with open(input_path, "w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["section"])
            writer.writerow(["IPE200"])
            writer.writerow([""])  # blank row should be dropped

        output_path = tmp_path / "out.csv"
        transform(
            str(input_path),
            str(output_path),
            [Mapping("id", lambda row: row["section"])],
        )

        with open(output_path, newline="") as handle:
            rows = list(csv.reader(handle))
        # header + the one non-blank data row only
        assert rows == [["id"], ["IPE200"]]
