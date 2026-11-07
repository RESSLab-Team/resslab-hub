"""
Unit tests for the contribution submission flow.

Pure-unit: GitHub is a fake client, validation is monkeypatched, and the
validator's database lookups are stubbed — nothing here needs Postgres.
"""

import json
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
    update_contribution,
)
from resslab_hub.contributions.trailers import build_commit_message, parse_trailers
from resslab_hub.data.uploader import Type
from resslab_hub.data.validator import TableValidator, ValidationResult
from resslab_hub.models.database.brace import Brace

CONTRIBUTOR = Contributor(
    name="Ada Lovelace",
    email="ada@example.edu",
    institution="EPFL",
    github_login="ada",
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

    def __init__(self, repo_files: dict, head_files=None, pull=None, pr_files=None):
        self.repo_files = repo_files
        #: Files as they are on the submission's branch (read with a ref).
        self.head_files = head_files or {}
        self.pull = pull
        self.pr_files = pr_files or []
        #: Commits on the submission's branch, oldest first.
        self.pr_commits: list = []
        self.committed: list = []
        self.deletions: list = []
        #: Path -> blob sha map the update sends so unchanged files are skipped.
        self.existing: dict = {}
        self.commit_kwargs: dict = {}
        self.pr: dict = {}
        self.deleted_branches: list = []
        self.fail_pr = False
        self.fail_ref_update = False
        #: Admins of the data repo, and the reviewers asked on the new PR.
        self.admins = ["dlignos", "Ada", "andskia"]
        self.reviewers: list = []
        self.fail_reviewers = False

    async def get_file_text(self, path, ref=None):
        if ref is not None and path in self.head_files:
            return self.head_files[path]
        return self.repo_files[path]

    async def get_pull(self, number):
        if self.pull is None:
            raise RuntimeError("not found")
        return self.pull

    async def list_pull_files(self, number):
        return self.pr_files

    async def list_pull_commits(self, number):
        return self.pr_commits

    async def update_pull_body(self, number, body):
        self.pr = {"number": number, "body": body}

    async def commit_on_branch(
        self, branch, head_sha, files, deletions, message, name, email, existing=None
    ):
        if self.fail_ref_update:
            raise RuntimeError("not a fast forward")
        self.committed = files
        self.deletions = deletions
        self.existing = existing
        self.commit_kwargs = {
            "branch": branch,
            "head_sha": head_sha,
            "message": message,
            "author_name": name,
            "author_email": email,
        }
        return "new-commit-sha"

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

    async def list_admin_logins(self):
        return self.admins

    async def request_reviewers(self, number, logins):
        if self.fail_reviewers:
            raise RuntimeError("Reviews may only be requested from collaborators")
        self.reviewers = logins


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
    # Provenance travels in the commit message, not in a file of its own.
    assert not [p for p in by_path if p.startswith("contributions/")]
    trailers = parse_trailers(client.commit_kwargs["message"])
    assert trailers["Submitted-by"] == ["Ada Lovelace <ada@example.edu>"]
    assert trailers["Institution"] == ["EPFL"]
    assert trailers["GitHub"] == ["@ada"]
    assert trailers["Dismissed-Warning"] == ["Value is far outside the range"]

    assert client.commit_kwargs["author_name"] == "Ada Lovelace"
    assert client.commit_kwargs["author_email"] == "ada@example.edu"
    assert "dismissed" in client.pr["body"]
    assert "Ada Lovelace" in client.pr["body"]


@pytest.mark.parametrize(
    "raw, detail",
    [
        ("{}", "JSON array"),
        ('["ok", 3]', "JSON array"),
        (json.dumps(["w"] * 101), "Too many"),
        (json.dumps(["x" * 501]), "too long"),
    ],
)
def test_parse_dismissed_refuses_bad_or_big_input(raw, detail):
    """The warnings go in the PR body and the trailers: bounded (#264 H4)."""
    from fastapi import HTTPException

    from resslab_hub.routers.contributions import _parse_dismissed

    with pytest.raises(HTTPException) as error:
        _parse_dismissed(raw)
    assert error.value.status_code == 400
    assert detail in error.value.detail


def test_parse_dismissed_keeps_the_limit_and_drops_blanks():
    from resslab_hub.routers.contributions import _parse_dismissed

    # 100 entries, the longest at the limit: accepted, the blank dropped.
    raw = json.dumps(["  far outside  ", "", *["w"] * 97, "x" * 500])
    parsed = _parse_dismissed(raw)
    assert parsed[0] == "far outside"
    assert len(parsed) == 99


def test_dismissed_warnings_cannot_mention_or_fake_a_field():
    """A warning is contributor text: no @mention, no fake ORCID line."""
    from resslab_hub.contributions.submission import build_pr_body
    from resslab_hub.routers.curation import _parse_pr_body

    contributor = Contributor(name="Ada Lovelace", email="ada@example.edu")
    body = build_pr_body(
        contributor,
        Type.ALL_BRACE,
        1,
        0,
        ["ping @someone", "x\n- **ORCID**: 0000-0000-0000-0001", "a `b` c"],
    )
    assert "- `ping @someone`" in body
    assert "- `x - **ORCID**: 0000-0000-0000-0001`" in body
    assert "- `a 'b' c`" in body
    _, parsed = _parse_pr_body(body)
    assert parsed.orcid in (None, "")


async def test_submit_pr_body_tells_how_to_update(tmp_path, monkeypatch):
    """The review discussion must show how to change a submission (#321)."""
    patch_validation(monkeypatch)
    client = FakeClient({"braces/steel_braces.csv": REPO_CSV})
    result = await submit_contribution(
        str(make_batch(tmp_path)), Type.ALL_BRACE, CONTRIBUTOR, [], client=client
    )

    assert result.head_sha == "commit-sha"
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


STATUS_REPO_CSV = (
    "id,f_y,name,data_curation_status\n"
    "B1,355,First,verified\n"
    "B2,275,Second,unverified\n"
)


async def test_submit_stamps_every_new_row_unverified(tmp_path, monkeypatch):
    # The batch cannot vouch for itself (#253): whatever it says, or with no
    # column at all, a new row goes in as unverified. Old rows keep theirs.
    patch_validation(monkeypatch)
    client = FakeClient({"braces/steel_braces.csv": STATUS_REPO_CSV})
    batch = make_batch(
        tmp_path, "id,f_y,name,data_curation_status\nB9,400,New one,verified\n"
    )
    await submit_contribution(
        str(batch), Type.ALL_BRACE, CONTRIBUTOR, [], client=client
    )
    merged = {f.path: f.content for f in client.committed}["braces/steel_braces.csv"]
    assert merged == STATUS_REPO_CSV + "B9,400,New one,unverified\n"


async def test_submit_without_the_column_is_stamped_too(tmp_path, monkeypatch):
    patch_validation(monkeypatch)
    client = FakeClient({"braces/steel_braces.csv": STATUS_REPO_CSV})
    await submit_contribution(
        str(make_batch(tmp_path)), Type.ALL_BRACE, CONTRIBUTOR, [], client=client
    )
    merged = {f.path: f.content for f in client.committed}["braces/steel_braces.csv"]
    assert merged.endswith("B9,400,New one,unverified\n")


async def test_submit_to_a_repo_without_the_column_adds_none(tmp_path, monkeypatch):
    # A data repository from before #253: nothing to stamp, nothing added.
    patch_validation(monkeypatch)
    client = FakeClient({"braces/steel_braces.csv": REPO_CSV})
    await submit_contribution(
        str(make_batch(tmp_path)), Type.ALL_BRACE, CONTRIBUTOR, [], client=client
    )
    merged = {f.path: f.content for f in client.committed}["braces/steel_braces.csv"]
    assert merged == REPO_CSV + "B9,400,New one\n"


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


# --- reviewers (#266) ------------------------------------------------------


async def test_submit_asks_the_admins_but_not_the_submitter(tmp_path, monkeypatch):
    patch_validation(monkeypatch)
    monkeypatch.setattr(submission.settings, "data_repo_reviewers", "admins")
    client = FakeClient({"braces/steel_braces.csv": REPO_CSV})
    await submit_contribution(
        str(make_batch(tmp_path)), Type.ALL_BRACE, CONTRIBUTOR, [], client=client
    )
    # "Ada" is the submitter's own login ("ada"), whatever the case.
    assert client.reviewers == ["dlignos", "andskia"]


async def test_submit_succeeds_when_reviewers_fail(tmp_path, monkeypatch):
    patch_validation(monkeypatch)
    monkeypatch.setattr(submission.settings, "data_repo_reviewers", "admins")
    client = FakeClient({"braces/steel_braces.csv": REPO_CSV})
    client.fail_reviewers = True
    result = await submit_contribution(
        str(make_batch(tmp_path)), Type.ALL_BRACE, CONTRIBUTOR, [], client=client
    )
    assert result.pr_number == 7
    assert client.deleted_branches == []


async def test_submit_with_reviewers_none_asks_nobody(tmp_path, monkeypatch):
    patch_validation(monkeypatch)
    monkeypatch.setattr(submission.settings, "data_repo_reviewers", "none")
    client = FakeClient({"braces/steel_braces.csv": REPO_CSV})
    client.admins = None  # would break if the admins were read
    await submit_contribution(
        str(make_batch(tmp_path)), Type.ALL_BRACE, CONTRIBUTOR, [], client=client
    )
    assert client.reviewers == []


async def test_submit_with_a_login_list_uses_it(tmp_path, monkeypatch):
    patch_validation(monkeypatch)
    monkeypatch.setattr(
        submission.settings, "data_repo_reviewers", " pierreleripoll, dlignos ,"
    )
    client = FakeClient({"braces/steel_braces.csv": REPO_CSV})
    await submit_contribution(
        str(make_batch(tmp_path)), Type.ALL_BRACE, CONTRIBUTOR, [], client=client
    )
    assert client.reviewers == ["pierreleripoll", "dlignos"]


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


# --- updating an open submission (#321) -------------------------------------

BRANCH = "contrib/braces/b9-abcd1234"
HEAD_CSV = REPO_CSV + "B9,400,New one\n"
#: What the PR looks like on GitHub. The sha is the file's blob id at the
#: branch head: the update sends it back so unchanged files skip their upload.
CURVE_PATH = "braces/force_displacement/B9.csv"
PR_FILES = [
    {"path": "braces/steel_braces.csv", "status": "modified", "sha": "sha-csv"},
    {"path": CURVE_PATH, "status": "added", "sha": "sha-curve"},
]


def hub_commits(name="Ada Lovelace", email="ada@example.edu") -> list:
    """The branch as the Hub left it: one commit carrying the trailers."""
    return [
        {
            "sha": "first-sha",
            "message": build_commit_message(
                "data(braces): add 1 experiment (B9)", name, email, institution="EPFL"
            ),
            "author_date": "2026-08-01T12:00:00Z",
        }
    ]


# A submission opened before trailers: no Hub commit, a JSON record instead.
PROVENANCE_PATH = "contributions/braces/abcd1234.json"
PROVENANCE = json.dumps(
    {
        "schema": 1,
        "type": "all-braces",
        "submitted_at": "2026-08-01T12:00:00+00:00",
        "contributor": {"name": "Ada Lovelace", "email": "ada@example.edu"},
        "files": [],
        "dismissed_warnings": [],
    }
)


def open_pull(**overrides) -> dict:
    pull = {
        "number": 7,
        "html_url": "https://github.com/x/pull/7",
        "state": "open",
        "head_ref": BRANCH,
        "head_sha": "head-sha",
    }
    pull.update(overrides)
    return pull


def edit_client(**overrides) -> FakeClient:
    client = FakeClient(
        {"braces/steel_braces.csv": REPO_CSV},
        head_files={"braces/steel_braces.csv": HEAD_CSV},
        pull=open_pull(**overrides),
        pr_files=list(PR_FILES),
    )
    client.pr_commits = hub_commits()
    return client


def legacy_edit_client(record: str = PROVENANCE, **overrides) -> FakeClient:
    """A branch from before trailers: the JSON record is all it has."""
    client = edit_client(**overrides)
    client.pr_commits = []
    client.pr_files.append({"path": PROVENANCE_PATH, "status": "added"})
    client.head_files[PROVENANCE_PATH] = record
    return client


async def update(tmpdir, client, head_sha="head-sha", dismissed=None):
    return await update_contribution(
        str(tmpdir), 7, head_sha, CONTRIBUTOR, dismissed or [], client=client
    )


async def test_update_replaces_the_batch_on_the_same_branch(tmp_path, monkeypatch):
    patch_validation(monkeypatch)
    client = edit_client()
    batch = make_batch(tmp_path, "id,f_y,name\nB9,450,Fixed one\n")

    result = await update(batch, client)

    assert result.pr_number == 7
    assert result.branch == BRANCH
    assert result.head_sha == "new-commit-sha"
    # The commit sits on the branch head, not on the base branch.
    assert client.commit_kwargs["head_sha"] == "head-sha"
    assert client.commit_kwargs["branch"] == BRANCH
    assert client.commit_kwargs["author_name"] == "Ada Lovelace"
    assert client.commit_kwargs["author_email"] == "ada@example.edu"
    assert client.commit_kwargs["message"].startswith(
        "data(braces): update 1 experiment"
    )

    by_path = {file.path: file.content for file in client.committed}
    merged = by_path["braces/steel_braces.csv"]
    # Rows the submission never owned are untouched; its own row is rewritten.
    assert merged.startswith(REPO_CSV.rstrip("\n"))
    assert "B9,450,Fixed one" in merged
    assert "B9,400,New one" not in merged
    assert merged.count("B9,") == 1
    assert client.deletions == []


async def test_update_stamps_the_batch_unverified(tmp_path, monkeypatch):
    patch_validation(monkeypatch)
    client = edit_client()
    client.repo_files["braces/steel_braces.csv"] = STATUS_REPO_CSV
    client.head_files["braces/steel_braces.csv"] = (
        STATUS_REPO_CSV + "B9,400,New one,unverified\n"
    )
    batch = make_batch(
        tmp_path, "id,f_y,name,data_curation_status\nB9,450,Fixed one,verified\n"
    )

    await update(batch, client)

    merged = {f.path: f.content for f in client.committed}["braces/steel_braces.csv"]
    assert merged == STATUS_REPO_CSV + "B9,450,Fixed one,unverified\n"


async def test_update_carries_the_editors_trailers(tmp_path, monkeypatch):
    patch_validation(monkeypatch)
    client = edit_client()
    batch = make_batch(tmp_path, "id,f_y,name\nB9,450,Fixed one\n")

    await update(batch, client, dismissed=["Value is far outside the range"])

    trailers = parse_trailers(client.commit_kwargs["message"])
    assert trailers["Submitted-by"] == ["Ada Lovelace <ada@example.edu>"]
    assert trailers["Dismissed-Warning"] == ["Value is far outside the range"]
    # Nothing is written under contributions/ any more.
    assert not [f for f in client.committed if f.path.startswith("contributions/")]


async def test_update_drops_a_legacy_record(tmp_path, monkeypatch):
    """The JSON left by the old code goes: the trailers now say the same."""
    patch_validation(monkeypatch)
    client = legacy_edit_client()
    batch = make_batch(tmp_path, "id,f_y,name\nB9,450,Fixed one\n")

    await update(batch, client)

    assert PROVENANCE_PATH in client.deletions
    assert not [f for f in client.committed if f.path.startswith("contributions/")]


async def test_update_deletes_a_file_the_batch_no_longer_has(tmp_path, monkeypatch):
    """Renaming a specimen must not leave the old curve file behind."""
    patch_validation(monkeypatch)
    client = edit_client()
    batch = write_archive(
        tmp_path,
        {
            "braces/steel_braces.csv": "id,f_y,name\nB10,450,Renamed\n",
            "braces/force_displacement/B10.csv": "Displacement [mm],Force [kN]\n0,0\n",
        },
    )

    await update(batch, client)

    assert client.deletions == ["braces/force_displacement/B9.csv"]
    by_path = {file.path: file.content for file in client.committed}
    assert "braces/force_displacement/B10.csv" in by_path
    assert "B10,450,Renamed" in by_path["braces/steel_braces.csv"]
    assert "B9" not in by_path["braces/steel_braces.csv"]


async def test_update_never_deletes_anything_but_its_own_curves(tmp_path, monkeypatch):
    patch_validation(monkeypatch)
    client = edit_client()
    client.pr_files.append({"path": ".github/workflows/ci.yml", "status": "modified"})
    batch = write_archive(
        tmp_path, {"braces/steel_braces.csv": "id,f_y,name\nB9,450,Fixed\n"}
    )

    await update(batch, client)

    # The stray file is classified "other" and left alone; only the submission's
    # own time-series file, absent from the new batch, goes.
    assert client.deletions == ["braces/force_displacement/B9.csv"]


async def test_update_escapes_formula_cells(tmp_path, monkeypatch):
    patch_validation(monkeypatch)
    client = edit_client()
    batch = make_batch(tmp_path, "id,f_y,name\nB9,-1.5,=cmd()\n")

    await update(batch, client)

    merged = {f.path: f.content for f in client.committed}["braces/steel_braces.csv"]
    assert "'=cmd()" in merged
    assert "-1.5" in merged


def provenance_by(**contributor) -> str:
    return json.dumps({**json.loads(PROVENANCE), "contributor": contributor})


async def test_update_refuses_someone_elses_submission(tmp_path, monkeypatch):
    """The address on the record decides, whichever way it was recorded."""
    patch_validation(monkeypatch)
    batch = make_batch(tmp_path, "id,f_y,name\nB9,450,Fixed one\n")
    by_trailers = edit_client()
    by_trailers.pr_commits = hub_commits(name="Grace Hopper", email="grace@example.edu")
    by_record = legacy_edit_client(
        provenance_by(name="Grace Hopper", email="grace@example.edu")
    )
    for client in (by_trailers, by_record):
        with pytest.raises(SubmissionError) as excinfo:
            await update(batch, client)
        assert excinfo.value.status_code == 403
        assert client.committed == []


async def test_update_refuses_a_fork(tmp_path, monkeypatch):
    """The App cannot push to a fork's branch: edit it on GitHub (#267)."""
    patch_validation(monkeypatch)
    client = edit_client(head_repo="someone/resslab-hub-data")
    with pytest.raises(SubmissionError) as excinfo:
        await update(make_batch(tmp_path, "id,f_y,name\nB9,450,Fixed one\n"), client)
    assert excinfo.value.status_code == 409
    assert "fork" in excinfo.value.detail
    assert client.committed == []


async def test_update_needs_a_readable_record(tmp_path, monkeypatch):
    """No trailers, no record, no owner: a hand-made branch is a curator's."""
    patch_validation(monkeypatch)
    client = edit_client()
    client.pr_commits = [{"sha": "x", "message": "fix: pushed by hand"}]
    with pytest.raises(SubmissionError) as excinfo:
        await update(make_batch(tmp_path, "id,f_y,name\nB9,450,Fixed one\n"), client)
    assert excinfo.value.status_code == 403


CURATOR = Contributor(name="Dimitrios Lignos", email="dl@epfl.ch", institution="EPFL")


async def test_a_curator_fixes_someone_elses_submission(tmp_path, monkeypatch):
    """The commit is the curator's, the submission stays the contributor's (#248)."""
    patch_validation(monkeypatch)
    client = edit_client()
    batch = make_batch(tmp_path, "id,f_y,name\nB9,450,Fixed one\n")

    result = await update_contribution(
        str(batch), 7, "head-sha", CURATOR, [], client=client, as_curator=True
    )

    assert result.head_sha == "new-commit-sha"
    assert client.commit_kwargs["author_name"] == "Dimitrios Lignos"
    assert client.commit_kwargs["author_email"] == "dl@epfl.ch"
    trailers = parse_trailers(client.commit_kwargs["message"])
    assert trailers["Submitted-by"] == ["Ada Lovelace <ada@example.edu>"]
    assert "Ada Lovelace (ada@example.edu)" in client.pr["body"]
    assert "dl@epfl.ch" not in client.pr["body"]


async def test_a_curator_cannot_fix_a_submission_nobody_owns(tmp_path, monkeypatch):
    """Their commit would become the first Hub commit, and so the owner."""
    patch_validation(monkeypatch)
    client = edit_client()
    client.pr_commits = [{"sha": "x", "message": "fix: pushed by hand"}]
    with pytest.raises(SubmissionError) as excinfo:
        await update_contribution(
            str(make_batch(tmp_path, "id,f_y,name\nB9,450,Fixed one\n")),
            7,
            "head-sha",
            CURATOR,
            [],
            client=client,
            as_curator=True,
        )
    assert excinfo.value.status_code == 403
    assert client.committed == []


async def test_update_falls_back_to_a_legacy_record(tmp_path, monkeypatch):
    """A submission opened before trailers stays editable by its author."""
    patch_validation(monkeypatch)
    client = legacy_edit_client()
    result = await update(
        make_batch(tmp_path, "id,f_y,name\nB9,450,Fixed one\n"), client
    )
    assert result.head_sha == "new-commit-sha"


async def test_update_ignores_the_case_of_the_address(tmp_path, monkeypatch):
    patch_validation(monkeypatch)
    client = edit_client()
    client.pr_commits = hub_commits(email="ADA@Example.edu")
    result = await update(
        make_batch(tmp_path, "id,f_y,name\nB9,450,Fixed one\n"), client
    )
    assert result.head_sha == "new-commit-sha"


async def test_update_by_another_address_of_the_same_account(tmp_path, monkeypatch):
    """Submitted from the EPFL address, edited with the gmail one main (#402)."""
    patch_validation(monkeypatch)
    client = edit_client()
    ada = Contributor(name="Ada Lovelace", email="ada@gmail.com", institution="EPFL")
    batch = make_batch(tmp_path, "id,f_y,name\nB9,450,Fixed one\n")

    with pytest.raises(SubmissionError) as excinfo:
        await update_contribution(str(batch), 7, "head-sha", ada, [], client=client)
    assert excinfo.value.status_code == 403

    result = await update_contribution(
        str(batch),
        7,
        "head-sha",
        ada,
        [],
        client=client,
        owner_emails=["ada@gmail.com", "ada@example.edu"],
    )
    assert result.head_sha == "new-commit-sha"
    assert client.commit_kwargs["author_email"] == "ada@gmail.com"


async def test_update_refuses_a_stale_head(tmp_path, monkeypatch):
    """A maintainer pushed meanwhile: the edit was written against the old file."""
    patch_validation(monkeypatch)
    client = edit_client()
    with pytest.raises(SubmissionError) as caught:
        await update(make_batch(tmp_path), client, head_sha="older-sha")
    assert caught.value.status_code == 409
    assert "Reload" in caught.value.detail
    assert client.committed == []


async def test_update_refuses_a_branch_the_hub_did_not_make(tmp_path, monkeypatch):
    patch_validation(monkeypatch)
    client = edit_client(head_ref="feature/hand-made")
    with pytest.raises(SubmissionError) as caught:
        await update(make_batch(tmp_path), client)
    assert caught.value.status_code == 404
    assert client.committed == []


async def test_update_refuses_a_closed_or_unknown_pull_request(tmp_path, monkeypatch):
    patch_validation(monkeypatch)
    closed = edit_client(state="closed")
    with pytest.raises(SubmissionError) as caught:
        await update(make_batch(tmp_path), closed)
    assert caught.value.status_code == 404

    missing = edit_client()
    missing.pull = None
    with pytest.raises(SubmissionError) as caught:
        await update(make_batch(tmp_path), missing)
    assert caught.value.status_code == 404


async def test_update_refuses_ids_already_in_the_repository(tmp_path, monkeypatch):
    patch_validation(monkeypatch)
    client = edit_client()
    batch = make_batch(tmp_path, "id,f_y,name\nB1,450,Taken\n")
    with pytest.raises(SubmissionError) as caught:
        await update(batch, client)
    assert caught.value.status_code == 409
    assert "already exist" in caught.value.detail


async def test_update_blocks_on_validation_errors(tmp_path, monkeypatch):
    failing = ValidationResult("steel_braces.csv")
    failing.add_error(1, "f_y", "x", "not a number")
    patch_validation(monkeypatch, [failing])
    client = edit_client()
    with pytest.raises(SubmissionValidationFailed):
        await update(make_batch(tmp_path), client)
    assert client.committed == []


async def test_update_rejects_paths_outside_the_layout(tmp_path, monkeypatch):
    patch_validation(monkeypatch)
    client = edit_client()
    batch = write_archive(
        tmp_path,
        {
            "braces/steel_braces.csv": "id,f_y,name\nB9,450,Fixed\n",
            ".github/workflows/evil.yml": "run: rm -rf /",
        },
    )
    with pytest.raises(SubmissionError) as caught:
        await update(batch, client)
    assert caught.value.status_code == 400
    assert client.committed == []


async def test_update_reports_a_branch_that_moved_mid_flight(tmp_path, monkeypatch):
    """The ref update is not forced, so GitHub refusing it means a race."""
    patch_validation(monkeypatch)
    client = edit_client()
    client.fail_ref_update = True
    with pytest.raises(SubmissionError) as caught:
        await update(make_batch(tmp_path), client)
    assert caught.value.status_code == 409
    assert "Reload" in caught.value.detail


async def test_update_refreshes_the_pull_request_summary(tmp_path, monkeypatch):
    """The review screen reads the counts off the body, so they must follow."""
    patch_validation(monkeypatch)
    client = edit_client()
    batch = write_archive(
        tmp_path,
        {
            "braces/steel_braces.csv": "id,f_y,name\nB9,450,Fixed\nB10,460,Second\n",
            "braces/force_displacement/B9.csv": "Displacement [mm],Force [kN]\n0,0\n",
            "braces/force_displacement/B10.csv": "Displacement [mm],Force [kN]\n0,0\n",
        },
    )

    await update(batch, client, dismissed=["Value is far outside the range"])

    body = client.pr["body"]
    assert "**Experiments**: 2" in body
    assert "**Time-series files**: 2" in body
    assert "Value is far outside the range" in body
    assert "### To update this submission" in body


async def test_update_survives_a_failed_summary_refresh(tmp_path, monkeypatch):
    """The data is committed by then; a stale summary must not fail the update."""
    patch_validation(monkeypatch)
    client = edit_client()

    async def boom(number, body):
        raise RuntimeError("GitHub said no")

    client.update_pull_body = boom

    result = await update(make_batch(tmp_path), client)
    assert result.head_sha == "new-commit-sha"


async def test_update_sends_the_branch_blob_shas(tmp_path, monkeypatch):
    """The commit needs them to skip re-uploading unchanged curves."""
    patch_validation(monkeypatch)
    client = edit_client()

    await update(make_batch(tmp_path), client)

    assert client.existing == {
        "braces/steel_braces.csv": "sha-csv",
        CURVE_PATH: "sha-curve",
    }


async def test_update_ignores_shas_of_files_deleted_on_the_branch(
    tmp_path, monkeypatch
):
    """A removed file's sha is its old content: never treat it as current."""
    patch_validation(monkeypatch)
    client = edit_client()
    client.pr_files = list(PR_FILES) + [
        {"path": "braces/force_displacement/B8.csv", "status": "removed", "sha": "old"}
    ]

    await update(make_batch(tmp_path), client)

    assert "braces/force_displacement/B8.csv" not in client.existing
