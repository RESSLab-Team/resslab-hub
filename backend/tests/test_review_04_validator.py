"""Review 04 (pipeline input): proofs on the validator report. No database.

``validate_all`` runs without Postgres: its database checks answer "nothing
found" when the database is not reachable. Each test states what the code
should do and is ``xfail(strict=True)`` until the finding is fixed.
Findings: docs/archive/review/findings/04-pipeline-input.md
"""

from pathlib import Path

import pytest

from resslab_hub.data.uploader import Type
from resslab_hub.data.validator import validate_all
from resslab_hub.models.database.brace import Brace
from resslab_hub.routers.root import _build_response
from tests.conftest import write_main_csv

PRIMARY = "braces/steel_braces.csv"


def _header(tmp_path: Path) -> tuple[str, str]:
    scratch = tmp_path / "header.csv"
    write_main_csv(scratch, Brace, [{"id": "B9"}])
    header, row = scratch.read_text().splitlines()
    scratch.unlink()
    return header, row


def _batch(tmp_path: Path, text: str) -> str:
    batch = tmp_path / "batch"
    target = batch / PRIMARY
    target.parent.mkdir(parents=True)
    target.write_text(text)
    return str(batch)


# --- 04-6: Python error text and the server's temp path ----------------------


def _unclosed_quote(header, row):
    return f'{header}\n{row}\n"B10,1\n'


def _long_cell(header, row):
    return f"{header}\n{row}\nB10," + "a" * 200_000 + "\n"


def _empty(header, row):
    return ""


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="review 04: 04-6")
@pytest.mark.parametrize("make", [_unclosed_quote, _long_cell, _empty])
def test_report_has_no_server_path_and_no_python_text(tmp_path, make):
    header, row = _header(tmp_path)
    batch = _batch(tmp_path, make(header, row))

    results = validate_all(Type.ALL_BRACE, [batch], cpu=1)
    report = _build_response(results, batch).model_dump_json()

    assert any(not result.is_valid() for result in results)
    assert batch not in report, "the absolute temp path is in the answer"
    assert "Failed to process file" not in report, "raw Python error text"


# --- 04-5: no cap on the number of errors ------------------------------------


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="review 04: 04-5")
def test_report_size_is_bounded(tmp_path):
    header, _ = _header(tmp_path)
    bad_row = ",".join(["<b>x</b>"] * len(header.split(",")))
    text = header + "\n" + "\n".join([bad_row] * 300) + "\n"
    batch = _batch(tmp_path, text)

    results = validate_all(Type.ALL_BRACE, [batch], cpu=1)
    report = _build_response(results, batch).model_dump_json()
    errors = sum(len(result.errors) for result in results)

    # Today: 13 200 errors and a 1.8 MB answer for a 195 kB CSV. Each error is
    # in the answer twice (structured results and the legacy string arrays).
    assert errors <= 1000, f"{errors} errors, answer {len(report)} B for {len(text)} B"
