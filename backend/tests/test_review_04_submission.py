"""Review 04 (pipeline input): proofs on the submission path. No database.

The validator's database lookups fail softly when Postgres is not reachable
(no stats, no existing ids), which is all these tests need. Each test states
what the code should do and is ``xfail(strict=True)`` until the finding is
fixed. Findings: docs/archive/review/findings/04-pipeline-input.md
"""

from pathlib import Path

import pytest

from resslab_hub.contributions.submission import (
    SubmissionError,
    _layout_for,
    _read_csv,
    batch_ids,
    build_primary_csv,
    read_batch,
)
from resslab_hub.data.uploader import Type
from resslab_hub.data.validator import TableValidator, parse_number, validate_all
from resslab_hub.models.database.brace import Brace
from tests.conftest import write_main_csv

PRIMARY = "braces/steel_braces.csv"


def _primary(tmp_path: Path, rows) -> Path:
    file_path = tmp_path / PRIMARY
    file_path.parent.mkdir(parents=True, exist_ok=True)
    write_main_csv(file_path, Brace, rows)
    return file_path


# --- 04-8: a file /validate accepts cannot be submitted -----------------------


@pytest.mark.xfail(strict=True, raises=UnicodeDecodeError, reason="review 04: 04-8")
@pytest.mark.parametrize("encoding", ["utf-16", "latin-1"])
def test_a_batch_validate_accepts_can_be_read_at_submit(tmp_path, encoding):
    file_path = _primary(tmp_path, [{"id": "B9", "investigator": "Müller"}])
    file_path.write_bytes(file_path.read_text(encoding="utf-8").encode(encoding))

    results = validate_all(Type.ALL_BRACE, [str(tmp_path)], cpu=1)
    # /validate says yes, with a warning only.
    assert all(result.is_valid() for result in results), [str(r) for r in results]

    # submit_contribution reads the same file as UTF-8: UnicodeDecodeError,
    # which _run_on_archive turns into a 500.
    _, _, ids = read_batch(str(tmp_path), _layout_for(Type.ALL_BRACE))
    assert ids == ["B9"]


# --- 04-9: two id columns -----------------------------------------------------


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="review 04: 04-9")
def test_validator_refuses_a_duplicated_header(tmp_path):
    file_path = _primary(tmp_path, [{"id": "B9"}])
    header, *rows = file_path.read_text().splitlines()
    file_path.write_text(f"{header},id\n{rows[0]},B1\n")

    result = TableValidator(Brace).validate_one(str(file_path))

    assert not result.is_valid(), "a CSV with two 'id' columns passes"


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="review 04: 04-9")
def test_the_id_written_is_the_id_checked():
    header, rows = _read_csv("id,f_y,name,id\nB9,400,New one,B1\n")

    # batch_ids reads the FIRST id column: the repo clash check sees B9.
    assert batch_ids(header, rows) == ["B9"]
    # build_primary_csv keeps the LAST one: the commit adds a second B1.
    merged = build_primary_csv(["id", "f_y", "name"], "\n", [], header, rows)
    written = merged.splitlines()[1].split(",")[0]

    assert written == "B9", f"checked B9, wrote {written}"


# --- 04-10: an unknown column -------------------------------------------------


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="review 04: 04-10")
def test_a_column_the_validator_only_warns_about_is_not_a_server_error(tmp_path):
    file_path = _primary(tmp_path, [{"id": "B9"}])
    header, *rows = file_path.read_text().splitlines()
    file_path.write_text(f"{header},colour\n{rows[0]},red\n")
    result = TableValidator(Brace).validate_one(str(file_path))
    assert result.is_valid(), str(result)  # a warning only

    header, rows = _read_csv(file_path.read_text())
    repo_header = header[:-1]
    with pytest.raises(SubmissionError) as refused:
        build_primary_csv(repo_header, "\n", [], header, rows)

    # Today: 502 "the data dictionary may have changed, contact the maintainers".
    assert refused.value.status_code < 500, refused.value.detail


# --- 04-11: numbers that only Python reads -------------------------------------


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="review 04: 04-11")
@pytest.mark.parametrize("cell", ["1_000", "-1_000", "١٢٣", "１２"])
def test_parse_number_refuses_what_the_database_and_the_editor_refuse(cell):
    # Decimal() accepts underscores and any Unicode digit. PostgreSQL 14 and
    # the editor's own DECIMAL pattern (utils/validation.ts) do not.
    value, message = parse_number(cell)
    assert value is None, f"{cell!r} read as {value}"
