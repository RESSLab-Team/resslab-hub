"""Pure-unit tests for the dashboard benchmark's row bootstrapper (no database).

What matters is that the generated table keeps the *shape* of the real one:
the distinct values of each categorical column, the share of empty cells, and
values the validator still accepts. If those drift, the browser numbers the
benchmark produces stop meaning anything.
"""

import csv
import random

from benchmark.bootstrap_rows import (
    DATABASES,
    bootstrap,
    column_types,
    looks_numeric,
    read_csv,
)

HEADER = ["id", "investigator", "shape", "date", "f_y", "displacement_count", "note"]
ROWS = [
    {
        "id": f"REAL-{i}",
        "investigator": ["Alice", "Bob", "Carol"][i % 3],
        "shape": ["HSS", "Wide Flange"][i % 2],
        "date": "2009",
        "f_y": f"{300 + i}.5",
        "displacement_count": "3",
        # Two rows in five have no note, so the empty share is 40 %.
        "note": "" if i % 5 < 2 else "a note",
    }
    for i in range(20)
]
TYPES = {
    "id": "string",
    "investigator": "string",
    "shape": "string",
    "date": "smallinteger",
    "f_y": "decimalfloat",
    "displacement_count": "smallinteger",
    "note": "string",
}


def generate(count=500, seed=354):
    return bootstrap(HEADER, ROWS, TYPES, count, "BRC", random.Random(seed))


class TestBootstrap:
    def test_writes_the_asked_number_of_rows_with_unique_ids(self):
        rows = generate(500)
        assert len(rows) == 500
        assert len({row["id"] for row in rows}) == 500
        assert rows[0]["id"] == "BENCH-BRC-00001"

    def test_keeps_every_column(self):
        assert list(generate(10)[0]) == HEADER

    def test_categorical_columns_keep_their_distinct_values(self):
        rows = generate(500)
        assert {row["investigator"] for row in rows} == {"Alice", "Bob", "Carol"}
        assert {row["shape"] for row in rows} == {"HSS", "Wide Flange"}

    def test_keeps_the_share_of_empty_cells(self):
        rows = generate(2000)
        empty = sum(1 for row in rows if not row["note"])
        # 40 % in the source; a random draw wanders a little around it.
        assert 0.35 < empty / len(rows) < 0.45

    def test_never_empties_a_column_that_was_always_filled(self):
        assert all(row["f_y"] for row in generate(500))

    def test_jitters_numbers_so_they_do_not_collapse_on_the_source_values(self):
        rows = generate(2000)
        # 20 source values, and the point of the jitter is to beat that.
        assert len({row["f_y"] for row in rows}) > 400

    def test_keeps_the_decimals_of_the_source(self):
        assert all(
            row["f_y"].split(".")[1:] and len(row["f_y"].split(".")[1]) == 1
            for row in generate(200)
        )

    def test_leaves_years_and_counts_alone(self):
        rows = generate(500)
        assert {row["date"] for row in rows} == {"2009"}
        assert {row["displacement_count"] for row in rows} == {"3"}

    def test_is_repeatable_for_one_seed(self):
        assert generate(200, seed=1) == generate(200, seed=1)
        assert generate(200, seed=1) != generate(200, seed=2)

    def test_falls_back_to_sniffing_when_the_dictionary_says_nothing(self):
        rows = bootstrap(HEADER, ROWS, {}, 300, "BRC", random.Random(354))
        # f_y is still recognised as a number and still jittered.
        assert len({row["f_y"] for row in rows}) > 100
        assert {row["shape"] for row in rows} == {"HSS", "Wide Flange"}


class TestColumnTypes:
    def test_reads_the_type_column_of_a_data_dictionary(self, tmp_path):
        path = tmp_path / "d.csv"
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["column_name", "type", "group"])
            writer.writerow(["id", "String", "x"])
            writer.writerow(["f_y", "DecimalFloat", "x"])
        assert column_types(path, ["id", "f_y"]) == {
            "id": "string",
            "f_y": "decimalfloat",
        }

    def test_is_empty_when_there_is_no_dictionary(self, tmp_path):
        assert column_types(tmp_path / "nope.csv", ["id"]) == {}

    def test_ignores_columns_the_dictionary_does_not_declare(self, tmp_path):
        path = tmp_path / "d.csv"
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["column_name", "type"])
            writer.writerow(["id", "String"])
        assert column_types(path, ["id", "extra"]) == {"id": "string"}


class TestDatabases:
    def test_every_database_derives_its_dictionary_from_its_csv(self):
        for key, database in DATABASES.items():
            assert database.dictionary_path.endswith("_data_dictionary.csv"), key
            assert database.csv_path.endswith(".csv"), key

    def test_reads_a_csv_with_a_byte_order_mark(self, tmp_path):
        path = tmp_path / "m.csv"
        path.write_bytes(b"\xef\xbb\xbfid,f_y\nB1,300\n")
        header, rows = read_csv(path)
        assert header == ["id", "f_y"]
        assert rows == [{"id": "B1", "f_y": "300"}]


class TestMissingMarkers:
    """`NA` / `NR` mean "no value" in the data repo; they must survive as-is."""

    HEADER = ["id", "f_y"]
    ROWS = [
        {"id": f"R{i}", "f_y": "NA" if i % 2 else f"{300 + i}.0"} for i in range(10)
    ]

    def test_markers_are_copied_not_jittered(self):
        rows = bootstrap(
            self.HEADER,
            self.ROWS,
            {"f_y": "decimalfloat"},
            400,
            "BRC",
            random.Random(1),
        )
        values = {row["f_y"] for row in rows}
        assert "NA" in values
        assert len(values) > 50  # the real numbers still got their jitter

    def test_a_column_full_of_markers_is_still_seen_as_numeric(self):
        assert looks_numeric(["NA", "300", "NR", ""])
        assert not looks_numeric(["NA", "Wide Flange"])
