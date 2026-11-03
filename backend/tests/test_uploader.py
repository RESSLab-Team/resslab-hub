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
    status_value,
    upload_all,
    upload_key,
    upload_one,
)
from resslab_hub.models.database.brace import Brace, BraceDisplacement
from resslab_hub.models.database.upload import UploadedFile
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


def test_status_is_read_from_the_file():
    headers = ["id", "data_curation_status"]
    assert status_value(headers, ["B1", "verified"]) == "verified"
    assert status_value(headers, ["B1", " unverified "]) == "unverified"


def test_status_defaults_to_unverified():
    # No column, an empty cell, a short row or an unknown word: the site
    # shows the warning rather than vouching for the data (#253).
    assert status_value(["id"], ["B1"]) == "unverified"
    assert status_value(["id", "data_curation_status"], ["B1", ""]) == "unverified"
    assert status_value(["id", "data_curation_status"], ["B1"]) == "unverified"
    assert status_value(["id", "data_curation_status"], ["B1", "ok"]) == "unverified"


def test_table_uploader_without_the_status_column(tmp_path, db_session):
    csv_path = tmp_path / "steel_braces.csv"
    write_main_csv(csv_path, Brace, [{"id": "B1"}])
    lines = csv_path.read_text(encoding="utf-8").splitlines()
    index = lines[0].split(",").index("data_curation_status")
    csv_path.write_text(
        "\n".join(
            ",".join(cell for i, cell in enumerate(line.split(",")) if i != index)
            for line in lines
        )
        + "\n",
        encoding="utf-8",
    )

    result = upload_one(Type.BRACE, str(csv_path))

    assert "1++" in result
    assert db_session.query(Brace).one().data_curation_status == "unverified"


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


# ---------------------------------------------------------------------------
# upload_all skips unchanged files and removes deleted ones (#405)
# ---------------------------------------------------------------------------
CURVE_HEADERS = ["Displacement [mm]", "Force [kN]"]
BRACE_KEYS = [
    "brace-displacement/B1.csv",
    "brace-displacement/B2.csv",
    "brace/steel_braces.csv",
    "readme/braces",
]


def make_braces(tmp_path):
    """A braces folder: main CSV (B1, B2), one curve each, a README."""
    root = tmp_path / "braces"
    (root / "force_displacement").mkdir(parents=True)
    write_main_csv(root / "steel_braces.csv", Brace, [{"id": "B1"}, {"id": "B2"}])
    (root / "README.md").write_text("# Braces\n", encoding="utf-8")
    for brace_id in ("B1", "B2"):
        write_measurement_csv(
            root / "force_displacement" / f"{brace_id}.csv",
            CURVE_HEADERS,
            [["0.0", "0.0"]],
        )
    return root


def hashes(db_session):
    db_session.expire_all()
    return {row.key: row for row in db_session.query(UploadedFile).all()}


def curve_rows(db_session, brace_id):
    return (
        db_session.query(BraceDisplacement)
        .filter(BraceDisplacement.brace_id == brace_id)
        .count()
    )


def test_upload_all_second_run_skips_everything(tmp_path, db_session):
    make_braces(tmp_path)
    first = upload_all(Type.ALL_BRACE, [str(tmp_path)])
    assert first.uploaded == BRACE_KEYS
    assert first.skipped == []

    second = upload_all(Type.ALL_BRACE, [str(tmp_path)])

    assert second.uploaded == []
    assert second.failed == []
    assert second.removed == []
    assert sorted(second.skipped) == BRACE_KEYS
    assert sorted(hashes(db_session)) == BRACE_KEYS
    assert curve_rows(db_session, "B1") == 1
    assert curve_rows(db_session, "B2") == 1


def test_upload_all_rewrites_only_the_changed_file(tmp_path, db_session):
    root = make_braces(tmp_path)
    upload_all(Type.ALL_BRACE, [str(tmp_path)])
    before = {
        key: (row.sha256, row.uploaded_at) for key, row in hashes(db_session).items()
    }

    write_measurement_csv(
        root / "force_displacement" / "B2.csv",
        CURVE_HEADERS,
        [["0.0", "0.0"], ["1.0", "5.0"]],
    )
    report = upload_all(Type.ALL_BRACE, [str(tmp_path)])

    assert report.uploaded == ["brace-displacement/B2.csv"]
    after = hashes(db_session)
    b1 = after["brace-displacement/B1.csv"]
    assert (b1.sha256, b1.uploaded_at) == before["brace-displacement/B1.csv"]
    assert (
        after["brace-displacement/B2.csv"].sha256
        != (before["brace-displacement/B2.csv"][0])
    )
    assert curve_rows(db_session, "B2") == 2


def test_upload_all_removes_the_rows_of_a_deleted_file(tmp_path, db_session):
    root = make_braces(tmp_path)
    upload_all(Type.ALL_BRACE, [str(tmp_path)])

    (root / "force_displacement" / "B1.csv").unlink()
    report = upload_all(Type.ALL_BRACE, [str(tmp_path)])

    assert report.removed == ["brace-displacement/B1.csv"]
    assert report.uploaded == []
    assert curve_rows(db_session, "B1") == 0
    assert curve_rows(db_session, "B2") == 1
    assert "brace-displacement/B1.csv" not in hashes(db_session)
    flags = {b.id: b.displacement_count for b in db_session.query(Brace).all()}
    assert flags == {"B1": 0, "B2": 1}


def test_upload_all_force_uploads_everything(tmp_path, db_session):
    make_braces(tmp_path)
    upload_all(Type.ALL_BRACE, [str(tmp_path)])

    report = upload_all(Type.ALL_BRACE, [str(tmp_path)], force=True)

    assert report.uploaded == BRACE_KEYS
    assert report.skipped == []


def test_upload_all_partial_runs_remove_nothing(tmp_path, db_session):
    root = make_braces(tmp_path)
    upload_all(Type.ALL_BRACE, [str(tmp_path)])

    # one file of one type: the other curves of that type are not gone
    one = upload_all(
        Type.BRACE_DISPLACEMENT, [str(root / "force_displacement" / "B1.csv")]
    )
    # the light upload keeps one curve per type: B2 is capped out, not gone
    light = upload_all(Type.ALL_BRACE, [str(tmp_path)], series_limit=1)

    assert one.removed == []
    assert light.removed == []
    assert curve_rows(db_session, "B2") == 1
    assert "brace-displacement/B2.csv" in hashes(db_session)


def test_upload_all_removes_nothing_without_the_main_csv(tmp_path, db_session):
    root = make_braces(tmp_path)
    upload_all(Type.ALL_BRACE, [str(tmp_path)])

    (root / "steel_braces.csv").unlink()
    (root / "force_displacement" / "B1.csv").unlink()
    report = upload_all(Type.ALL_BRACE, [str(tmp_path)])

    assert report.removed == []
    assert curve_rows(db_session, "B1") == 1
    assert "brace-displacement/B1.csv" in hashes(db_session)


def test_upload_all_failed_file_gets_no_hash(tmp_path, db_session):
    root = make_braces(tmp_path)
    # no brace B9 in the main CSV: the COPY fails on the foreign key
    write_measurement_csv(
        root / "force_displacement" / "B9.csv", CURVE_HEADERS, [["0.0", "0.0"]]
    )

    report = upload_all(Type.ALL_BRACE, [str(tmp_path)])

    assert [r.key for r in report.failed] == ["brace-displacement/B9.csv"]
    assert "brace-displacement/B9.csv" not in hashes(db_session)
    # so the next run tries it again
    again = upload_all(Type.ALL_BRACE, [str(tmp_path)])
    assert [r.key for r in again.failed] == ["brace-displacement/B9.csv"]


def test_upload_key():
    assert upload_key(Type.README, "/x/braces/README.md") == "readme/braces"
    assert upload_key(Type.README, "/x/material/cyclic_coupons/README.md") == (
        "readme/cyclic"
    )
    assert upload_key(Type.README, "/x/unknown/README.md") is None
    assert upload_key(Type.DICTIONARY, "/x/foo_data_dictionary.csv") is None
    assert upload_key(Type.DICTIONARY, "/x/steel_braces_data_dictionary.csv") == (
        "dictionary/steel_braces_data_dictionary.csv"
    )
    assert upload_key(Type.BRACE_DISPLACEMENT, "/x/B1.csv") == (
        "brace-displacement/B1.csv"
    )
