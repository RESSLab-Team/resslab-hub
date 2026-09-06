"""
Tests for the CSV -> database uploader (``resslab_hub.data.uploader``).

These tests pin the upload behaviour that must stay identical regardless of how
the rows are written to the database: value conversions, merge/update +
delete-outdated semantics for main tables, and delete-and-replace round-trips
for measurement tables. (The measurement path is bulk-rewritten to ``COPY ...
FROM STDIN`` on later branches; these behaviour-level assertions are what verify
that rewrite preserved the result.)
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import Boolean, Column, Date, Numeric, SmallInteger, String

from resslab_hub.data.count_flags import recompute_count_flags
from resslab_hub.data.uploader import (
    CsvFileUploader,
    TableUploader,
    Type,
    Uploader,
    cap_series,
    upload_all,
    upload_one,
)
from resslab_hub.models.database.brace import Brace, BraceDisplacement
from tests.conftest import write_main_csv, write_measurement_csv

# The conversion routine is a name-mangled private static method; bind it once.
get_value = TableUploader._TableUploader__get_value


def convert(column_type, value):
    """Run one raw CSV value through the uploader's type conversion."""
    column = Column("c", column_type)
    return get_value(column, ["c"], [value])


# ---------------------------------------------------------------------------
# __get_value conversions
# ---------------------------------------------------------------------------
def test_string_sentinels():
    assert convert(String(), "") == ""
    assert convert(String(), "NA") == "Not applicable"
    assert convert(String(), "nr") == "Not reported"
    assert convert(String(), "NaN") == "Not a number"
    assert convert(String(), "S355") == "S355"


def test_numeric_sentinels_and_values():
    assert convert(Numeric(), "") is None
    assert convert(Numeric(), "NA") is None
    assert convert(Numeric(), "NR") is None
    assert convert(Numeric(), "2.5") == Decimal("2.5")


def test_integer_via_decimal():
    assert convert(SmallInteger(), "3") == 3
    assert convert(SmallInteger(), "3.0") == 3
    assert isinstance(convert(SmallInteger(), "3"), int)


def test_boolean_yes_no_and_invalid():
    assert convert(Boolean(), "yes") is True
    assert convert(Boolean(), "No") is False
    with pytest.raises(ValueError):
        convert(Boolean(), "maybe")


def test_date_two_supported_formats():
    assert convert(Date(), "01.02.20") == date(2020, 2, 1)
    assert convert(Date(), "01.02.2020") == date(2020, 2, 1)
    with pytest.raises(ValueError):
        convert(Date(), "2020-02-01")


# ---------------------------------------------------------------------------
# TableUploader round-trip + update/delete (main entity table)
# ---------------------------------------------------------------------------
def test_table_uploader_roundtrip(tmp_path, db_session):
    csv_path = tmp_path / "steel_braces.csv"
    write_main_csv(
        csv_path,
        Brace,
        [
            {
                "id": "B1",
                "investigator": "Tester",
                "cross_section_shape": "HSS",
                "date": "2015",
                "f_yn": "355.5",
                "area": "NA",  # nullable numeric -> None
                "b_br": "",  # empty numeric -> None
            },
            {
                "id": "B2",
                "investigator": "Other",
                "cross_section_shape": "Wide Flange",
                "date": "2019",
            },
        ],
    )

    result = upload_one(Type.BRACE, str(csv_path))
    assert "2++" in result  # two rows added

    rows = {b.id: b for b in db_session.query(Brace).all()}
    assert set(rows) == {"B1", "B2"}
    b1 = rows["B1"]
    assert b1.investigator == "Tester"
    assert b1.cross_section_shape == "HSS"
    assert b1.date == 2015
    assert b1.f_yn == Decimal("355.5")
    assert b1.area is None
    assert b1.b_br is None


def test_table_uploader_update_and_delete(tmp_path, db_session):
    csv_path = tmp_path / "steel_braces.csv"
    write_main_csv(
        csv_path,
        Brace,
        [
            {"id": "B1", "investigator": "First"},
            {"id": "B2", "investigator": "Second"},
        ],
    )
    upload_one(Type.BRACE, str(csv_path))

    # Re-upload: B1 modified, B2 dropped from the file.
    write_main_csv(
        csv_path,
        Brace,
        [
            {"id": "B1", "investigator": "Modified"},
        ],
    )
    result = upload_one(Type.BRACE, str(csv_path))
    assert "0++" in result and "1**" in result and "1--" in result

    rows = {b.id: b for b in db_session.query(Brace).all()}
    assert set(rows) == {"B1"}
    assert rows["B1"].investigator == "Modified"


# ---------------------------------------------------------------------------
# CsvFileUploader round-trip via COPY (measurement table)
# ---------------------------------------------------------------------------
def _seed_brace(tmp_path, brace_id="B1"):
    csv_path = tmp_path / "steel_braces.csv"
    write_main_csv(csv_path, Brace, [{"id": brace_id}])
    upload_one(Type.BRACE, str(csv_path))


def test_csv_file_uploader_roundtrip(tmp_path, db_session):
    _seed_brace(tmp_path, "B1")

    measurement = tmp_path / "B1.csv"  # filename stem is the parent id
    write_measurement_csv(
        measurement,
        ["Displacement [mm]", "Force [kN]"],
        [["0.0", "0.0"], ["1.5", "10.0"], ["3.0", "20.0"]],
    )
    upload_one(Type.BRACE_DISPLACEMENT, str(measurement))

    rows = (
        db_session.query(BraceDisplacement)
        .filter(BraceDisplacement.brace_id == "B1")
        .order_by(BraceDisplacement.id)
        .all()
    )
    assert [r.id for r in rows] == [0, 1, 2]  # id == row index
    assert all(r.brace_id == "B1" for r in rows)
    assert [float(r.displacement) for r in rows] == [0.0, 1.5, 3.0]
    assert [float(r.force) for r in rows] == [0.0, 10.0, 20.0]


def test_csv_file_uploader_replaces_not_appends(tmp_path, db_session):
    _seed_brace(tmp_path, "B1")
    measurement = tmp_path / "B1.csv"

    write_measurement_csv(
        measurement,
        ["Displacement [mm]", "Force [kN]"],
        [["0.0", "0.0"], ["1.0", "5.0"], ["2.0", "10.0"]],
    )
    upload_one(Type.BRACE_DISPLACEMENT, str(measurement))

    # Re-upload with fewer rows: the parent's rows are wiped and re-inserted.
    write_measurement_csv(
        measurement,
        ["Displacement [mm]", "Force [kN]"],
        [["0.0", "0.0"]],
    )
    upload_one(Type.BRACE_DISPLACEMENT, str(measurement))

    rows = (
        db_session.query(BraceDisplacement)
        .filter(BraceDisplacement.brace_id == "B1")
        .all()
    )
    assert len(rows) == 1


def test_uploader_classes_share_interface():
    """Both concrete uploaders implement the common ``Uploader`` interface."""
    assert issubclass(TableUploader, Uploader)
    assert issubclass(CsvFileUploader, Uploader)


# ---------------------------------------------------------------------------
# DictionaryUploader
# ---------------------------------------------------------------------------
DICTIONARY_HEADER = "column_name,description,symbol,unit,type,example_value,nullable"
# The group column arrived with RESSLab-Team/resslab-hub-data#46.
DICTIONARY_HEADER_WITH_GROUP = DICTIONARY_HEADER + ",group"


def write_dictionary_csv(tmp_path, rows, header=DICTIONARY_HEADER):
    # The basename selects the target database ("braces").
    file_path = tmp_path / "steel_braces_data_dictionary.csv"
    file_path.write_text(header + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
    return file_path


def test_dictionary_uploader_roundtrip(tmp_path, db_session):
    from resslab_hub.models.database.dictionary import DictionaryColumn

    file_path = write_dictionary_csv(
        tmp_path,
        [
            "id,Unique identifier,,-,String,B1,False",
            "area,Cross-section area,A,mm2,DecimalFloat,120.5,True",
        ],
    )
    upload_one(Type.DICTIONARY, str(file_path))

    rows = (
        db_session.query(DictionaryColumn)
        .filter(DictionaryColumn.database == "braces")
        .order_by(DictionaryColumn.position)
        .all()
    )
    assert [row.column_name for row in rows] == ["id", "area"]
    assert rows[0].nullable is False
    assert rows[1].unit == "mm2"
    assert rows[1].example == "120.5"
    # A dictionary without the group column still uploads.
    assert [row.group for row in rows] == ["", ""]


def test_dictionary_uploader_reads_the_group_column(tmp_path, db_session):
    from resslab_hub.models.database.dictionary import DictionaryColumn

    file_path = write_dictionary_csv(
        tmp_path,
        [
            "id,Unique identifier,,-,String,B1,False,Experimental program details",
            "area,Cross-section area,A,mm2,DecimalFloat,120.5,True,Section properties",
        ],
        header=DICTIONARY_HEADER_WITH_GROUP,
    )
    upload_one(Type.DICTIONARY, str(file_path))

    rows = (
        db_session.query(DictionaryColumn)
        .filter(DictionaryColumn.database == "braces")
        .order_by(DictionaryColumn.position)
        .all()
    )
    assert [row.group for row in rows] == [
        "Experimental program details",
        "Section properties",
    ]


def test_dictionary_uploader_replaces_previous_rows(tmp_path, db_session):
    from resslab_hub.models.database.dictionary import DictionaryColumn

    upload_one(
        Type.DICTIONARY,
        str(
            write_dictionary_csv(
                tmp_path, ["id,Old,,-,String,B1,False", "gone,Old,,-,String,x,True"]
            )
        ),
    )
    upload_one(
        Type.DICTIONARY,
        str(write_dictionary_csv(tmp_path, ["id,New,,-,String,B1,False"])),
    )

    rows = (
        db_session.query(DictionaryColumn)
        .filter(DictionaryColumn.database == "braces")
        .all()
    )
    assert [row.column_name for row in rows] == ["id"]
    assert rows[0].description == "New"


def test_readme_uploader_keys_by_folder(tmp_path, db_session):
    from resslab_hub.models.database.dictionary import DatabaseReadme

    folder = tmp_path / "data" / "material" / "cyclic_coupons"
    folder.mkdir(parents=True)
    file_path = folder / "README.md"
    file_path.write_text("# Cyclic coupons\n\nGuide.\n", encoding="utf-8")
    upload_one(Type.README, str(file_path))

    row = db_session.get(DatabaseReadme, "cyclic")
    assert row is not None
    assert row.content.startswith("# Cyclic coupons")


def test_readme_uploader_replaces_previous_content(tmp_path, db_session):
    from resslab_hub.models.database.dictionary import DatabaseReadme

    folder = tmp_path / "braces"
    folder.mkdir()
    file_path = folder / "README.md"
    file_path.write_text("old", encoding="utf-8")
    upload_one(Type.README, str(file_path))
    file_path.write_text("new", encoding="utf-8")
    upload_one(Type.README, str(file_path))

    assert db_session.get(DatabaseReadme, "braces").content == "new"


def test_readme_uploader_skips_unknown_folder(tmp_path, db_session):
    from resslab_hub.models.database.dictionary import DatabaseReadme

    file_path = tmp_path / "README.md"
    file_path.write_text("root readme", encoding="utf-8")
    message = upload_one(Type.README, str(file_path))

    assert "Skipping" in message
    assert db_session.query(DatabaseReadme).count() == 0


# ---------------------------------------------------------------------------
# Derived *_count flags
# ---------------------------------------------------------------------------
def test_recompute_count_flags_follows_child_rows(tmp_path, db_session):
    _seed_brace(tmp_path, "B1")
    assert db_session.query(Brace).one().displacement_count == 0  # server default

    measurement = tmp_path / "B1.csv"
    write_measurement_csv(
        measurement,
        ["Displacement [mm]", "Force [kN]"],
        [["0.0", "0.0"], ["1.0", "5.0"]],
    )
    upload_one(Type.BRACE_DISPLACEMENT, str(measurement))
    recompute_count_flags(db_session)
    db_session.commit()
    assert db_session.query(Brace).one().displacement_count == 1

    # Re-upload the measurement file empty: rows are wiped, flag drops back.
    write_measurement_csv(measurement, ["Displacement [mm]", "Force [kN]"], [])
    upload_one(Type.BRACE_DISPLACEMENT, str(measurement))
    recompute_count_flags(db_session)
    db_session.commit()
    assert db_session.query(Brace).one().displacement_count == 0


def test_upload_all_recomputes_flags(tmp_path, db_session):
    """upload_all sets the flags itself — no manual recompute step."""
    root = tmp_path / "braces"
    root.mkdir()
    write_main_csv(root / "steel_braces.csv", Brace, [{"id": "B1"}, {"id": "B2"}])
    measurements = root / "force_displacement"
    measurements.mkdir()
    write_measurement_csv(
        measurements / "B1.csv",
        ["Displacement [mm]", "Force [kN]"],
        [["0.0", "0.0"]],
    )

    upload_all(Type.ALL_BRACE, [str(tmp_path)])

    flags = {b.id: b.displacement_count for b in db_session.query(Brace).all()}
    assert flags == {"B1": 1, "B2": 0}


# ---------------------------------------------------------------------------
# cap_series: the pure filter behind `upload-data-light` (per-worktree light DB)
# ---------------------------------------------------------------------------
def test_cap_series_caps_measurements_but_keeps_everything_else():
    args = [
        (Type.BRACE, "braces/steel_braces.csv"),
        (Type.DICTIONARY, "braces/steel_braces_data_dictionary.csv"),
        (Type.DICTIONARY, "columns/steel_columns_data_dictionary.csv"),
        (Type.README, "braces/README.md"),
        (Type.README, "columns/README.md"),
        (Type.BRACE_DISPLACEMENT, "braces/force_displacement/b.csv"),
        (Type.BRACE_DISPLACEMENT, "braces/force_displacement/a.csv"),
        (Type.COLUMN_MOMENT_STRONG, "columns/moment_rotation_strong/x.csv"),
    ]

    capped = cap_series(args, 1)

    # main tables and every per-folder dictionary/README survive untouched
    for kept in args[:5]:
        assert kept in capped
    # one file per series type, chosen alphabetically so reruns are identical
    assert (Type.BRACE_DISPLACEMENT, "braces/force_displacement/a.csv") in capped
    assert (Type.BRACE_DISPLACEMENT, "braces/force_displacement/b.csv") not in capped
    assert (Type.COLUMN_MOMENT_STRONG, "columns/moment_rotation_strong/x.csv") in capped
    assert len(capped) == 7
