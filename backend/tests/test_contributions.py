"""
Unit tests for the contribution submission flow.

Pure-unit: GitHub is a fake client, validation is monkeypatched, and the
validator's database lookups are stubbed — nothing here needs Postgres.
"""

from pathlib import Path

import pytest

from resslab_hub.contributions import submission
from resslab_hub.contributions.submission import (
    Contributor,
    SubmissionError,
    SubmissionValidationFailed,
    batch_ids,
    check_paths,
    escape_formula,
    flag_repo_duplicates,
    normalize_csv_text,
    repo_ids,
    submit_contribution,
)
from resslab_hub.data.uploader import Type
from resslab_hub.data.validator import TableValidator, ValidationResult
from resslab_hub.models.database.brace import Brace

CONTRIBUTOR = Contributor(
    name="Ada Lovelace", email="ada@example.edu", institution="EPFL"
)

REPO_CSV = "id,f_y,name\nB1,355,First\nB2,275,Second\n"


def write_archive(tmp_path: Path, files: dict) -> Path:
    for rel, content in files.items():
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    return tmp_path


class FakeClient:
    """In-memory DataRepoClient double recording every call."""

    def __init__(self, repo_files: dict):
        self.repo_files = repo_files
        self.committed: list = []
        self.commit_kwargs: dict = {}
        self.pr: dict = {}
        self.deleted_branches: list = []
        self.fail_pr = False

    async def get_file_text(self, path, ref=None):
        return self.repo_files[path]

    async def get_base_sha(self):
        return "base-sha"

    async def commit_files(self, branch, base_sha, files, message, name, email):
        self.committed = files
        self.commit_kwargs = {
            "branch": branch,
            "base_sha": base_sha,
            "message": message,
            "author_name": name,
            "author_email": email,
        }
        return "commit-sha"

    async def create_pull_request(self, branch, title, body):
        if self.fail_pr:
            raise RuntimeError("boom")
        self.pr = {"branch": branch, "title": title, "body": body}
        return {"url": "https://github.com/x/pull/7", "number": 7}

    async def delete_branch(self, branch):
        self.deleted_branches.append(branch)


def valid_result() -> ValidationResult:
    return ValidationResult("steel_braces.csv")


def patch_validation(monkeypatch, results=None):
    monkeypatch.setattr(
        submission, "validate_all", lambda *a, **k: results or [valid_result()]
    )


# --- escape_formula ---------------------------------------------------------


@pytest.mark.parametrize(
    ("cell", "expected"),
    [
        ("=SUM(A1:A9)", "'=SUM(A1:A9)"),
        ("@import", "'@import"),
        ("+41 21 693 11 11", "'+41 21 693 11 11"),
        ("-DROP TABLE", "'-DROP TABLE"),
        ("-1.5", "-1.5"),  # negative numbers are data, not formulas
        ("+2e3", "+2e3"),
        ("hello", "hello"),
        ("NR", "NR"),
    ],
)
def test_escape_formula(cell, expected):
    assert escape_formula(cell) == expected


# --- path allowlist ---------------------------------------------------------


def test_check_paths_accepts_known_layout(tmp_path):
    write_archive(
        tmp_path,
        {
            "braces/steel_braces.csv": REPO_CSV,
            "braces/force_displacement/B9.csv": "a,b\n1,2\n",
        },
    )
    layout = check_paths(str(tmp_path), Type.ALL_BRACE)
    assert layout.primary_csv == "braces/steel_braces.csv"


@pytest.mark.parametrize(
    "bad_path",
    [
        ".github/workflows/evil.yml",  # workflow injection
        "braces/evil.sh",  # non-CSV beside the primary
        "columns/steel_columns.csv",  # wrong component directory
        "braces/force_displacement/.hidden.csv",  # leading dot
        "braces/force_displacement/deep/B1.csv",  # unexpected nesting
    ],
)
def test_check_paths_rejects_unknown_locations(tmp_path, bad_path):
    write_archive(
        tmp_path,
        {"braces/steel_braces.csv": REPO_CSV, bad_path: "x"},
    )
    with pytest.raises(SubmissionError) as caught:
        check_paths(str(tmp_path), Type.ALL_BRACE)
    assert caught.value.status_code == 400


# --- batch ids --------------------------------------------------------------


def test_batch_ids_rejects_duplicates_and_bad_names():
    header = ["id", "f_y"]
    with pytest.raises(SubmissionError) as caught:
        batch_ids(header, [["B9", "1"], ["B9", "2"]])
    assert caught.value.status_code == 409
    with pytest.raises(SubmissionError):
        batch_ids(header, [["../evil", "1"]])
    with pytest.raises(SubmissionError):
        batch_ids(header, [["", "1"]])
    assert batch_ids(header, [["B9", "1"], ["B10.a", "2"]]) == ["B9", "B10.a"]


@pytest.mark.parametrize(
    "specimen_id",
    [
        "Mukaide_et_al_2016__P3325-C+",  # a real hss_columns id
        "S355 φ10 C1",  # spaces and non-Latin letters
        "RC#1",
        "A(1)",
    ],
)
def test_batch_ids_accepts_real_world_names(specimen_id):
    assert batch_ids(["id"], [[specimen_id]]) == [specimen_id]


@pytest.mark.parametrize(
    "specimen_id",
    ["a/b", "a\\b", "a:b", ".hidden", "_x", "-x", "a?b", "a*b", "a\tb"],
)
def test_batch_ids_rejects_unsafe_file_names(specimen_id):
    with pytest.raises(SubmissionError) as caught:
        batch_ids(["id"], [[specimen_id]])
    assert caught.value.status_code == 400
    assert "file name" in caught.value.detail


# --- submission flow --------------------------------------------------------


def make_batch(tmp_path, csv_text="id,f_y,name\nB9,400,New one\n"):
    return write_archive(
        tmp_path,
        {
            "braces/steel_braces.csv": csv_text,
            "braces/force_displacement/B9.csv": "Displacement [mm],Force [kN]\n0,0\n",
        },
    )


async def test_submit_happy_path(tmp_path, monkeypatch):
    patch_validation(monkeypatch)
    client = FakeClient({"braces/steel_braces.csv": REPO_CSV})
    result = await submit_contribution(
        str(make_batch(tmp_path)),
        Type.ALL_BRACE,
        CONTRIBUTOR,
        ["Value is far outside the range"],
        client=client,
    )

    assert result.pr_url == "https://github.com/x/pull/7"
    assert result.pr_number == 7
    assert result.branch.startswith("contrib/braces/b9-")

    by_path = {file.path: file.content for file in client.committed}
    merged = by_path["braces/steel_braces.csv"]
    # Existing rows kept, batch row appended.
    assert merged.startswith(REPO_CSV.rstrip("\n"))
    assert "B9,400,New one" in merged
    assert "braces/force_displacement/B9.csv" in by_path
    provenance_path = next(p for p in by_path if p.startswith("contributions/braces/"))
    assert '"identity": "self-declared"' in by_path[provenance_path]
    assert "Value is far outside the range" in by_path[provenance_path]

    assert client.commit_kwargs["author_name"] == "Ada Lovelace"
    assert client.commit_kwargs["author_email"] == "ada@example.edu"
    assert "dismissed" in client.pr["body"]
    assert "Ada Lovelace" in client.pr["body"]


async def test_submit_pr_body_tells_how_to_update(tmp_path, monkeypatch):
    """The review discussion must show how to change a submission (#321)."""
    patch_validation(monkeypatch)
    client = FakeClient({"braces/steel_braces.csv": REPO_CSV})
    result = await submit_contribution(
        str(make_batch(tmp_path)), Type.ALL_BRACE, CONTRIBUTOR, [], client=client
    )

    body = client.pr["body"]
    assert "### To update this submission" in body
    assert "do not open a second submission" in body
    # The edit link points at the primary CSV on the submission's own branch.
    assert f"/blob/{result.branch}/braces/steel_braces.csv" in body


async def test_submit_escapes_formula_cells(tmp_path, monkeypatch):
    patch_validation(monkeypatch)
    client = FakeClient({"braces/steel_braces.csv": REPO_CSV})
    batch = make_batch(tmp_path, "id,f_y,name\nB9,-1.5,=cmd()\n")
    await submit_contribution(
        str(batch), Type.ALL_BRACE, CONTRIBUTOR, [], client=client
    )
    merged = {f.path: f.content for f in client.committed}["braces/steel_braces.csv"]
    assert "'=cmd()" in merged
    assert "-1.5" in merged and "'-1.5" not in merged


async def test_submit_blocks_on_validation_errors(tmp_path, monkeypatch):
    failed = valid_result()
    failed.add_error(1, "f_y", "x", "Must be a number")
    patch_validation(monkeypatch, [failed])
    with pytest.raises(SubmissionValidationFailed):
        await submit_contribution(
            str(make_batch(tmp_path)),
            Type.ALL_BRACE,
            CONTRIBUTOR,
            [],
            client=FakeClient({"braces/steel_braces.csv": REPO_CSV}),
        )


async def test_submit_rejects_repo_duplicates(tmp_path, monkeypatch):
    patch_validation(monkeypatch)
    client = FakeClient({"braces/steel_braces.csv": REPO_CSV})
    batch = make_batch(tmp_path, "id,f_y,name\nB2,400,Clash\n")
    with pytest.raises(SubmissionError) as caught:
        await submit_contribution(
            str(batch), Type.ALL_BRACE, CONTRIBUTOR, [], client=client
        )
    assert caught.value.status_code == 409
    assert "B2" in caught.value.detail
    assert client.pr == {}


async def test_submit_rejects_header_drift(tmp_path, monkeypatch):
    # The repo CSV lacks batch columns entirely -> real schema drift.
    patch_validation(monkeypatch)
    client = FakeClient({"braces/steel_braces.csv": "id,other\nB1,1\n"})
    with pytest.raises(SubmissionError) as caught:
        await submit_contribution(
            str(make_batch(tmp_path)), Type.ALL_BRACE, CONTRIBUTOR, [], client=client
        )
    assert caught.value.status_code == 502
    assert "f_y" in caught.value.detail


async def test_submit_aligns_to_repo_column_order_and_extras(tmp_path, monkeypatch):
    # Real repo CSVs can order columns differently from the dictionary and
    # keep legacy extras (hss_columns' test_id); rows align by name, extras NR.
    patch_validation(monkeypatch)
    repo = "test_id,id,name,f_y\n1,B1,First,355\n"
    client = FakeClient({"braces/steel_braces.csv": repo})
    await submit_contribution(
        str(make_batch(tmp_path)), Type.ALL_BRACE, CONTRIBUTOR, [], client=client
    )
    merged = {f.path: f.content for f in client.committed}["braces/steel_braces.csv"]
    lines = merged.strip().split("\n")
    assert lines[0] == "test_id,id,name,f_y"
    assert lines[-1] == "NR,B9,New one,400"


async def test_read_csv_strips_bom(tmp_path, monkeypatch):
    patch_validation(monkeypatch)
    client = FakeClient({"braces/steel_braces.csv": "\ufeff" + REPO_CSV})
    result = await submit_contribution(
        str(make_batch(tmp_path)), Type.ALL_BRACE, CONTRIBUTOR, [], client=client
    )
    assert result.pr_number == 7


async def test_submit_cleans_up_branch_on_pr_failure(tmp_path, monkeypatch):
    patch_validation(monkeypatch)
    client = FakeClient({"braces/steel_braces.csv": REPO_CSV})
    client.fail_pr = True
    with pytest.raises(SubmissionError) as caught:
        await submit_contribution(
            str(make_batch(tmp_path)), Type.ALL_BRACE, CONTRIBUTOR, [], client=client
        )
    assert caught.value.status_code == 502
    assert len(client.deleted_branches) == 1


async def test_submit_unsupported_type(tmp_path, monkeypatch):
    def raise_unimplemented(*a, **k):
        raise NotImplementedError

    monkeypatch.setattr(submission, "validate_all", raise_unimplemented)
    with pytest.raises(SubmissionError) as caught:
        await submit_contribution(
            str(make_batch(tmp_path)),
            Type.ALL_BRACE,
            CONTRIBUTOR,
            [],
            client=FakeClient({}),
        )
    assert caught.value.status_code == 422


# --- repo duplicate check inside /validate ----------------------------------


def primary_result(tmp_path) -> ValidationResult:
    target = tmp_path / "braces" / "steel_braces.csv"
    return ValidationResult(target.name, str(target))


async def test_flag_repo_duplicates_marks_ids_at_repo_head(tmp_path, monkeypatch):
    monkeypatch.setattr(submission, "_repo_ids_cache", {})
    make_batch(tmp_path, "id,f_y,name\nB9,400,New\nB1,300,Clash\n\nB2,1,Clash\n")
    result = primary_result(tmp_path)
    await flag_repo_duplicates(
        str(tmp_path),
        Type.ALL_BRACE,
        [result],
        client=FakeClient({"braces/steel_braces.csv": REPO_CSV}),
    )
    assert [(err.row, err.value) for err in result.errors] == [(2, "B1"), (4, "B2")]
    assert all(err.column == "id" for err in result.errors)
    assert "data repository" in result.errors[0].message


async def test_flag_repo_duplicates_skips_ids_already_flagged(tmp_path, monkeypatch):
    # The validator already reported B1 as a database duplicate: one error.
    monkeypatch.setattr(submission, "_repo_ids_cache", {})
    make_batch(tmp_path, "id,f_y,name\nB1,300,Clash\n")
    result = primary_result(tmp_path)
    result.add_error(1, "id", "B1", "already exists in the database")
    await flag_repo_duplicates(
        str(tmp_path),
        Type.ALL_BRACE,
        [result],
        client=FakeClient({"braces/steel_braces.csv": REPO_CSV}),
    )
    assert len(result.errors) == 1


async def test_flag_repo_duplicates_without_primary_result(tmp_path, monkeypatch):
    monkeypatch.setattr(submission, "_repo_ids_cache", {})
    make_batch(tmp_path)
    await flag_repo_duplicates(str(tmp_path), Type.ALL_BRACE, [], client=FakeClient({}))


async def test_repo_ids_are_cached_per_type(monkeypatch):
    monkeypatch.setattr(submission, "_repo_ids_cache", {})
    calls = []

    class CountingClient(FakeClient):
        async def get_file_text(self, path, ref=None):
            calls.append(path)
            return await super().get_file_text(path, ref)

    client = CountingClient({"braces/steel_braces.csv": REPO_CSV})
    assert await repo_ids(Type.ALL_BRACE, client) == {"B1", "B2"}
    assert await repo_ids(Type.ALL_BRACE, client) == {"B1", "B2"}
    assert calls == ["braces/steel_braces.csv"]


# --- duplicate-id check in the validator ------------------------------------


def brace_csv(tmp_path, rows: str) -> str:
    header = ",".join(col.key for col in Brace.__table__.c)
    target = tmp_path / "steel_braces.csv"
    target.write_text(f"{header}\n{rows}")
    return str(target)


def stub_db(monkeypatch, existing: set):
    monkeypatch.setattr(TableValidator, "_range_stats", lambda self: {})
    monkeypatch.setattr(TableValidator, "_existing_ids", lambda self: existing)


def duplicate_errors(result: ValidationResult) -> list:
    return [err for err in result.errors if "already exists" in err.message]


def test_validator_flags_ids_already_in_database(tmp_path, monkeypatch):
    stub_db(monkeypatch, {"B1"})
    columns = list(Brace.__table__.c)
    row = ",".join("B1" if col.key == "id" else "NR" for col in columns)
    validator = TableValidator(Brace, check_duplicate_ids=True)
    result = validator.validate_one(brace_csv(tmp_path, f"{row}\n"))
    errors = duplicate_errors(result)
    assert len(errors) == 1
    assert errors[0].row == 1
    assert errors[0].column == "id"


def test_validator_flags_in_batch_duplicates(tmp_path, monkeypatch):
    stub_db(monkeypatch, set())
    columns = list(Brace.__table__.c)
    row = ",".join("B9" if col.key == "id" else "NR" for col in columns)
    validator = TableValidator(Brace, check_duplicate_ids=True)
    result = validator.validate_one(brace_csv(tmp_path, f"{row}\n{row}\n"))
    assert any("more than once" in err.message for err in result.errors)


def test_validator_reports_unsafe_ids_on_the_cell(tmp_path, monkeypatch):
    # The submission would refuse the id anyway; the validator flags it first
    # so the editor shows the problem on the id field during the auto-check.
    stub_db(monkeypatch, set())
    columns = list(Brace.__table__.c)
    row = ",".join("a/b" if col.key == "id" else "NR" for col in columns)
    validator = TableValidator(Brace)
    result = validator.validate_one(brace_csv(tmp_path, f"{row}\n"))
    errors = [err for err in result.errors if "file name" in err.message]
    assert len(errors) == 1
    assert (errors[0].row, errors[0].column) == (1, "id")


def test_validator_accepts_ids_with_plus_and_unicode(tmp_path, monkeypatch):
    stub_db(monkeypatch, set())
    columns = list(Brace.__table__.c)
    row = ",".join("S355 φ10 C+" if col.key == "id" else "NR" for col in columns)
    result = TableValidator(Brace).validate_one(brace_csv(tmp_path, f"{row}\n"))
    assert not [err for err in result.errors if err.column == "id"]


def test_validator_default_skips_duplicate_check(tmp_path, monkeypatch):
    stub_db(monkeypatch, {"B1"})
    columns = list(Brace.__table__.c)
    row = ",".join("B1" if col.key == "id" else "NR" for col in columns)
    validator = TableValidator(Brace)
    result = validator.validate_one(brace_csv(tmp_path, f"{row}\n"))
    assert duplicate_errors(result) == []


def test_check_range_mixes_float_stats_with_decimal_values():
    # An all-zero Float column (count>=20, min==max==0.0) used to crash with
    # "unsupported operand type(s) for -: 'float' and 'decimal.Decimal'".
    result = ValidationResult("steel_material.csv")
    TableValidator._check_range(result, 1, "col", "5", {"col": (20, 0.0, 0.0)})
    assert len(result.warnings) == 1  # 5 is far outside [0, 0]

    quiet = ValidationResult("steel_material.csv")
    TableValidator._check_range(quiet, 1, "col", "0.5", {"col": (20, 0.0, 0.0)})
    assert quiet.warnings == []
    assert quiet.errors == []


async def test_submit_normalizes_time_series_line_endings(tmp_path, monkeypatch):
    # Spreadsheet exports come with a BOM, CRLF endings and no final newline;
    # the data repository's CI rejects all three, so the PR must not carry them.
    patch_validation(monkeypatch)
    client = FakeClient({"braces/steel_braces.csv": REPO_CSV})
    batch = write_archive(
        tmp_path,
        {
            "braces/steel_braces.csv": "id,f_y,name\nB9,400,New one\n",
            "braces/force_displacement/B9.csv": (
                "\ufeffDisplacement [mm],Force [kN]\r\n0,0\r\n1,2"
            ),
        },
    )
    await submit_contribution(
        str(batch), Type.ALL_BRACE, CONTRIBUTOR, [], client=client
    )
    by_path = {f.path: f.content for f in client.committed}
    assert by_path["braces/force_displacement/B9.csv"] == (
        "Displacement [mm],Force [kN]\n0,0\n1,2\n"
    )


@pytest.mark.parametrize(
    "text, expected",
    [
        ("a,b\n1,2\n", "a,b\n1,2\n"),
        ("a,b\r\n1,2", "a,b\n1,2\n"),
        ("a,b\r1,2\r", "a,b\n1,2\n"),
        ("\ufeffa,b\n1,2\n\n\n", "a,b\n1,2\n"),
        ("", ""),
    ],
)
def test_normalize_csv_text(text, expected):
    assert normalize_csv_text(text) == expected


async def test_submit_preserves_repo_crlf_line_endings(tmp_path, monkeypatch):
    patch_validation(monkeypatch)
    crlf_repo = REPO_CSV.replace("\n", "\r\n")
    client = FakeClient({"braces/steel_braces.csv": crlf_repo})
    await submit_contribution(
        str(make_batch(tmp_path)), Type.ALL_BRACE, CONTRIBUTOR, [], client=client
    )
    merged = {f.path: f.content for f in client.committed}["braces/steel_braces.csv"]
    # The untouched part of the file is byte-identical; the new row follows suit.
    assert merged.startswith(crlf_repo)
    assert merged.endswith("B9,400,New one\r\n")
