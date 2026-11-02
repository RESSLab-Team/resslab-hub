"""
Unit tests for the read-only curation endpoints.

Pure-unit: GitHub is a fake client, validation is monkeypatched — nothing here
needs Postgres or the network.
"""

import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from resslab_hub.config import settings
from resslab_hub.contributions.projection import (
    classify_files,
    type_for_branch,
    type_for_files,
)
from resslab_hub.contributions.submission import Contributor, build_pr_body
from resslab_hub.contributions.trailers import build_commit_message
from resslab_hub.data.uploader import Type
from resslab_hub.data.validator import ValidationResult
from resslab_hub.routers import curation
from resslab_hub.routers.curation import (
    _parse_pr_body,
    get_contribution,
    get_contribution_comments,
    get_contribution_file,
    get_contribution_validation,
    list_contributions,
)
from resslab_hub.utils.rate_limit import limiter

BASE_CSV = "id,f_y,name\nB1,355,First\nB2,275,Second\n"
HEAD_CSV = BASE_CSV + "B9,400,New one\n"
CURVE_CSV = "Displacement [mm],Force [kN]\n0,0\n1,10\n"

CONTRIBUTOR = Contributor(
    name="Ada Lovelace",
    email="ada@example.edu",
    institution="EPFL",
    orcid="0000-1",
    github_login="ada",
)

HUB_COMMITS = [
    {
        "sha": "first-sha",
        "message": build_commit_message(
            "data(braces): add 1 experiment (B9)",
            "Ada Lovelace",
            "ada@example.edu",
            institution="EPFL",
            orcid="0000-1",
            github_login="ada",
            dismissed_warnings=["Value is far outside the range"],
        ),
        "author_date": "2026-08-01T12:00:00+00:00",
    }
]

# A submission opened before trailers: the JSON record answers instead.
PROVENANCE_PATH = "contributions/braces/abcd1234.json"
PROVENANCE = json.dumps(
    {
        "schema": 1,
        "type": "all-braces",
        "submitted_at": "2026-08-01T12:00:00+00:00",
        "contributor": {
            "name": "Ada Lovelace",
            "email": "ada@example.edu",
            "institution": "EPFL",
            "orcid": "0000-1",
        },
        "files": [],
        "dismissed_warnings": ["Value is far outside the range"],
    }
)


def make_pull(**overrides) -> dict:
    pull = {
        "number": 7,
        "html_url": "https://github.com/x/pull/7",
        "title": "data(braces): add 1 experiment (B9)",
        "state": "open",
        "draft": False,
        "head_ref": "contrib/braces/b9-abcd1234",
        "head_sha": "head-sha",
        "base_ref": "main",
        "created_at": "2026-08-01T12:00:00+00:00",
        "updated_at": "2026-08-01T12:00:00+00:00",
        "body": build_pr_body(CONTRIBUTOR, Type.ALL_BRACE, 1, 1, []),
        "author": "resslab-hub-contribution-pipeline[bot]",
        "author_type": "Bot",
    }
    pull.update(overrides)
    return pull


def make_comment(**overrides) -> dict:
    comment = {
        "id": 101,
        "author": "dlignos",
        "author_type": "User",
        "body": "Could you confirm the coupon orientation?",
        "html_url": "https://github.com/x/pull/7#issuecomment-101",
        "created_at": "2026-08-02T09:00:00+00:00",
        "updated_at": "2026-08-02T09:00:00+00:00",
    }
    comment.update(overrides)
    return comment


PR_COMMENTS = [
    make_comment(),
    make_comment(
        id=102,
        author="resslab-hub-contribution-pipeline[bot]",
        author_type="Bot",
        body="Validation re-ran: 0 errors.",
        created_at="2026-08-02T10:00:00+00:00",
    ),
]


PR_FILES = [
    {"path": "braces/steel_braces.csv", "status": "modified"},
    {"path": "braces/force_displacement/B9.csv", "status": "added"},
    {"path": "contributions/braces/abcd1234.json", "status": "added"},
]


class FakeClient:
    """In-memory double for the curation read path."""

    def __init__(
        self,
        pulls=None,
        files=None,
        texts=None,
        comments=None,
        commits=None,
        files_by_number=None,
    ):
        self.pulls = pulls if pulls is not None else [make_pull()]
        self.files = files if files is not None else list(PR_FILES)
        #: Changed files of one pull request; the others get ``files``.
        self.files_by_number = files_by_number or {}
        self.list_calls = 0
        self.file_calls = 0
        self.commits = commits if commits is not None else list(HUB_COMMITS)
        self.comments = comments if comments is not None else list(PR_COMMENTS)
        #: Counts GitHub round-trips so a test can prove the TTL cache holds.
        self.comment_calls = 0
        # (path, ref) -> text; ref None = base branch.
        self.texts = (
            texts
            if texts is not None
            else {
                ("braces/steel_braces.csv", "head-sha"): HEAD_CSV,
                ("braces/steel_braces.csv", None): BASE_CSV,
                ("braces/force_displacement/B9.csv", "head-sha"): CURVE_CSV,
                ("contributions/braces/abcd1234.json", "head-sha"): PROVENANCE,
            }
        )

    async def list_open_pulls(self):
        self.list_calls += 1
        return self.pulls

    async def get_pull(self, number):
        for pull in self.pulls:
            if pull["number"] == number:
                return pull
        raise RuntimeError("not found")

    async def list_pull_files(self, number):
        self.file_calls += 1
        return self.files_by_number.get(number, self.files)

    async def list_pull_commits(self, number):
        return self.commits

    async def get_file_text(self, path, ref=None):
        return self.texts[(path, ref)]

    async def list_issue_comments(self, number):
        self.comment_calls += 1
        return self.comments


#: Who calls, as ``get_current_user`` leaves it on the request. A curator by
#: default: most tests are about the projection, not about access.
CURATOR = SimpleNamespace(id="curator-id", email="grace@example.edu", role="curator")
OWNER = SimpleNamespace(id="owner-id", email="Ada@Example.edu", role="contributor")
STRANGER = SimpleNamespace(id="other-id", email="bob@example.edu", role="contributor")


def make_request(user=CURATOR) -> Request:
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/contributions",
            "headers": [],
            "query_string": b"",
            "client": ("127.0.0.1", 80),
            "server": ("test", 80),
            "scheme": "http",
        }
    )
    if user is not None:
        request.state.user = user
    return request


@pytest.fixture(autouse=True)
def curation_env(monkeypatch):
    """Fresh cache, no rate limiting, GitHub App 'configured'."""
    monkeypatch.setattr(curation, "_cache", curation._TTLCache())
    monkeypatch.setattr(limiter, "enabled", False)
    monkeypatch.setattr(curation, "configured", lambda: True)
    yield


def use_client(monkeypatch, client: FakeClient):
    monkeypatch.setattr(curation, "DataRepoClient", lambda: client)


# --- helpers ----------------------------------------------------------------


def test_type_for_branch():
    assert type_for_branch("contrib/braces/b9-ab12") is Type.ALL_BRACE
    assert type_for_branch("contrib/hss-columns/x-1") is Type.ALL_HSS_COLUMN
    assert type_for_branch("contrib/unknown/x-1") is None
    assert type_for_branch("contrib/braces") is None
    assert type_for_branch("feature/braces/x") is None


def test_parse_pr_body_roundtrip():
    body = build_pr_body(CONTRIBUTOR, Type.ALL_BRACE, 3, 2, ["w1"])
    count, contributor = _parse_pr_body(body)
    assert count == 3
    assert contributor.name == "Ada Lovelace"
    assert contributor.institution == "EPFL"
    assert contributor.orcid == "0000-1"
    # The @mention that notifies the contributor of every review comment.
    assert contributor.github_login == "ada"


def test_parse_pr_body_roundtrip_with_update_help():
    """The update section must not disturb the fields the review screen reads."""
    body = build_pr_body(
        CONTRIBUTOR,
        Type.ALL_BRACE,
        3,
        2,
        ["w1"],
        "contrib/braces/b9-abcd1234",
        "braces/steel_braces.csv",
    )
    count, contributor = _parse_pr_body(body)
    assert count == 3
    assert contributor.name == "Ada Lovelace"
    assert contributor.institution == "EPFL"


def test_parse_pr_body_tolerates_free_text():
    count, contributor = _parse_pr_body("A hand-written PR body.")
    assert count is None
    assert contributor is None


def test_classify_files():
    classified = {f.path: f for f in classify_files(PR_FILES, Type.ALL_BRACE)}
    assert classified["braces/steel_braces.csv"].kind == "primary"
    curve = classified["braces/force_displacement/B9.csv"]
    assert curve.kind == "timeseries"
    assert curve.timeseries_dir == "braces/force_displacement"
    assert curve.experiment_id == "B9"
    assert classified["contributions/braces/abcd1234.json"].kind == "provenance"
    extra = classify_files([{"path": ".github/workflows/evil.yml"}], Type.ALL_BRACE)
    assert extra[0].kind == "other"


def test_type_for_files():
    def files(*paths):
        return [{"path": p, "status": "modified"} for p in paths]

    assert type_for_files(files("columns/steel_columns.csv")) == (
        Type.ALL_COLUMN,
        "",
    )
    # A dictionary or a README alone is still one database's pull request.
    assert type_for_files(files("braces/README.md"))[0] is Type.ALL_BRACE
    assert (
        type_for_files(files("hss_columns/hss_columns_data_dictionary.csv"))[0]
        is Type.ALL_HSS_COLUMN
    )
    # Files outside every database folder do not count.
    assert (
        type_for_files(files("braces/steel_braces.csv", ".github/x.yml", "README.md"))[
            0
        ]
        is Type.ALL_BRACE
    )
    assert type_for_files(files(".github/workflows/x.yml")) == (
        None,
        "No database file changed.",
    )
    # The material family shares a parent folder but is three databases.
    input_type, reason = type_for_files(
        files("material/cyclic_coupons/README.md", "material/tensile_coupons/README.md")
    )
    assert input_type is None
    assert "material/cyclic_coupons" in reason
    assert "material/tensile_coupons" in reason
    input_type, reason = type_for_files(files("braces/README.md", "columns/README.md"))
    assert input_type is None
    assert reason == "Changes 2 databases: columns, braces."


# --- list -------------------------------------------------------------------

COLUMN_FILES = [{"path": "columns/steel_columns.csv", "status": "modified"}]
TWO_DATABASES = [
    {"path": "braces/README.md", "status": "modified"},
    {"path": "columns/README.md", "status": "modified"},
]


async def test_list_keeps_every_pull_request(monkeypatch):
    """Nothing is dropped without a trace (#267)."""
    client = FakeClient(
        pulls=[
            make_pull(),
            make_pull(number=8, head_ref="feat/curation-status", body="By hand."),
            make_pull(number=9, head_ref="docs/readmes", body="By hand."),
            make_pull(number=10, head_ref="contrib/not-a-type/x-1"),
        ],
        files_by_number={8: COLUMN_FILES, 9: TWO_DATABASES},
    )
    use_client(monkeypatch, client)
    response = await list_contributions(make_request())
    assert response.configured is True
    items = {item.pr_number: item for item in response.items}
    assert list(items) == [7, 8, 9, 10]

    assert items[7].kind == "submission"
    assert items[7].type == "all-braces"
    assert items[7].experiment_count == 1
    assert items[7].contributor.name == "Ada Lovelace"

    assert items[8].kind == "manual"
    assert items[8].type == "all-columns"
    assert items[8].reason == ""
    assert items[8].contributor is None

    assert items[9].kind == "unrecognised"
    assert items[9].type == ""
    assert items[9].reason == "Changes 2 databases: columns, braces."

    # An unknown slug is read like any other branch: from its files.
    assert items[10].kind == "manual"
    assert items[10].type == "all-braces"


async def test_list_skips_verification_pulls_and_says_so(monkeypatch, caplog):
    client = FakeClient(
        pulls=[make_pull(), make_pull(number=11, head_ref="verify/braces/b1-abcd")]
    )
    use_client(monkeypatch, client)
    with caplog.at_level("INFO", logger="resslab_hub.routers.curation"):
        response = await list_contributions(make_request())
    assert [item.pr_number for item in response.items] == [7]
    assert "skipped #11 (verify/braces/b1-abcd)" in caplog.text
    # The branch said it all: no files call for it.
    assert client.file_calls == 0


async def test_list_shows_a_pull_request_whose_files_fail(monkeypatch, caplog):
    class Failing(FakeClient):
        async def list_pull_files(self, number):
            raise RuntimeError("GitHub is down")

    use_client(monkeypatch, Failing(pulls=[make_pull(number=8, head_ref="feat/x")]))
    response = await list_contributions(make_request())
    assert [item.kind for item in response.items] == ["unrecognised"]
    assert response.items[0].reason == "Its files could not be read from GitHub."
    assert "files of #8 could not be read" in caplog.text


async def test_list_keeps_drafts_and_flags_forks(monkeypatch):
    client = FakeClient(
        pulls=[
            make_pull(draft=True, head_repo=str(settings.data_repo)),
            make_pull(number=8, head_repo="someone/resslab-hub-data"),
            make_pull(number=9, head_repo=""),
        ]
    )
    use_client(monkeypatch, client)
    items = {i.pr_number: i for i in (await list_contributions(make_request())).items}
    assert items[7].draft is True
    assert items[7].from_fork is False
    assert items[8].from_fork is True
    # A deleted fork leaves no head repo: not counted as a fork.
    assert items[9].from_fork is False


async def test_list_fresh_drops_the_cache(monkeypatch):
    client = FakeClient()
    use_client(monkeypatch, client)
    await list_contributions(make_request())
    await list_contributions(make_request())
    assert client.list_calls == 1
    await list_contributions(make_request(), fresh=True)
    assert client.list_calls == 2


async def test_list_reads_files_once_per_head_sha(monkeypatch):
    client = FakeClient(
        pulls=[make_pull(number=8, head_ref="feat/x")],
        files_by_number={8: COLUMN_FILES},
    )
    use_client(monkeypatch, client)
    await list_contributions(make_request())
    await list_contributions(make_request(), fresh=True)
    assert client.file_calls == 1
    client.pulls = [make_pull(number=8, head_ref="feat/x", head_sha="new-sha")]
    await list_contributions(make_request(), fresh=True)
    assert client.file_calls == 2


async def test_list_unconfigured(monkeypatch):
    monkeypatch.setattr(curation, "configured", lambda: False)
    response = await list_contributions(make_request())
    assert response.configured is False
    assert response.items == []


# --- detail -----------------------------------------------------------------


async def test_detail_reconstructs_batch(monkeypatch):
    client = FakeClient()
    use_client(monkeypatch, client)
    detail = await get_contribution(make_request(), 7)
    assert detail.columns == ["id", "f_y", "name"]
    assert [e.id for e in detail.experiments] == ["B9"]
    assert detail.experiments[0].cells == {"id": "B9", "f_y": "400", "name": "New one"}
    assert detail.contributor.orcid == "0000-1"
    assert detail.contributor.institution == "EPFL"
    # The trailers carry it; the old JSON path never did.
    assert detail.contributor.github_login == "ada"
    assert detail.submitted_at == "2026-08-01T12:00:00+00:00"
    assert detail.dismissed_warnings == ["Value is far outside the range"]
    assert detail.reconstruction_warning is None


async def test_detail_reads_a_legacy_record(monkeypatch):
    """A submission opened before trailers still shows its contributor."""
    client = FakeClient(commits=[])
    client.texts[(PROVENANCE_PATH, "head-sha")] = PROVENANCE
    use_client(monkeypatch, client)
    detail = await get_contribution(make_request(), 7)
    assert detail.contributor.name == "Ada Lovelace"
    assert detail.contributor.orcid == "0000-1"
    assert detail.submitted_at == "2026-08-01T12:00:00+00:00"
    assert detail.dismissed_warnings == ["Value is far outside the range"]
    assert detail.reconstruction_warning is None


async def test_detail_handles_crlf_and_header_drift(monkeypatch):
    # Head CSV in repo order with a legacy extra column and CRLF endings.
    head = "test_id,id,name,f_y\r\n1,B1,First,355\r\nNR,B9,New one,400\r\n"
    base = "test_id,id,name,f_y\r\n1,B1,First,355\r\n"
    client = FakeClient(
        texts={
            ("braces/steel_braces.csv", "head-sha"): head,
            ("braces/steel_braces.csv", None): base,
        }
    )
    use_client(monkeypatch, client)
    detail = await get_contribution(make_request(), 7)
    assert detail.columns == ["test_id", "id", "name", "f_y"]
    assert [e.id for e in detail.experiments] == ["B9"]
    assert detail.experiments[0].cells["f_y"] == "400"


async def test_detail_flags_unreadable_provenance(monkeypatch):
    """No trailers and no readable record: say so, do not break the screen."""
    client = FakeClient(commits=[{"sha": "x", "message": "pushed by hand"}])
    client.texts[(PROVENANCE_PATH, "head-sha")] = "not json"
    use_client(monkeypatch, client)
    detail = await get_contribution(make_request(), 7)
    # Contributor falls back to the PR body; the warning is set.
    assert detail.contributor.name == "Ada Lovelace"
    assert "commit trailers" in detail.reconstruction_warning


async def test_detail_flags_count_mismatch(monkeypatch):
    client = FakeClient(
        pulls=[make_pull(body=build_pr_body(CONTRIBUTOR, Type.ALL_BRACE, 2, 1, []))]
    )
    use_client(monkeypatch, client)
    detail = await get_contribution(make_request(), 7)
    assert len(detail.experiments) == 1
    assert "experiment count" in detail.reconstruction_warning


async def test_detail_404_on_closed_or_foreign(monkeypatch):
    use_client(monkeypatch, FakeClient(pulls=[make_pull(state="closed")]))
    with pytest.raises(HTTPException) as caught:
        await get_contribution(make_request(), 7)
    assert caught.value.status_code == 404

    # The pull request is cached by number: start each case from scratch.
    monkeypatch.setattr(curation, "_cache", curation._TTLCache())
    use_client(
        monkeypatch,
        FakeClient(pulls=[make_pull(head_ref="feature/x")], files=TWO_DATABASES),
    )
    with pytest.raises(HTTPException) as caught:
        await get_contribution(make_request(), 7)
    assert caught.value.status_code == 404
    assert "Changes 2 databases" in caught.value.detail

    monkeypatch.setattr(curation, "_cache", curation._TTLCache())
    use_client(monkeypatch, FakeClient(pulls=[make_pull(head_ref="verify/braces/x")]))
    with pytest.raises(HTTPException) as caught:
        await get_contribution(make_request(), 7)
    assert caught.value.status_code == 404


async def test_detail_opens_a_pull_request_opened_by_hand(monkeypatch):
    use_client(
        monkeypatch,
        FakeClient(
            pulls=[make_pull(head_ref="feat/new-brace", body="A hand-written body.")],
            files=PR_FILES[:2],
            commits=[],
        ),
    )
    detail = await get_contribution(make_request(), 7)
    assert detail.kind == "manual"
    assert detail.type == "all-braces"
    assert [e.id for e in detail.experiments] == ["B9"]
    assert detail.reconstruction_warning == curation.MANUAL_WARNING


async def test_detail_says_whether_it_is_mine(monkeypatch):
    """Per request, never from the cache: two people read the same detail."""
    use_client(monkeypatch, FakeClient())
    assert (await get_contribution(make_request(CURATOR), 7)).mine is False
    assert (await get_contribution(make_request(OWNER), 7)).mine is True


# --- who can read a submission (#248) -----------------------------------------


async def _read_everything(request):
    """Every per-PR endpoint, as the review and the edit screens call them."""
    await get_contribution(request, 7)
    await get_contribution_validation(request, 7)
    await get_contribution_comments(request, 7)
    await get_contribution_file(request, 7, "braces/force_displacement/B9.csv")


@pytest.fixture
def no_validation(monkeypatch):
    def fake_validate(input_type, dirs, cpu, check_duplicate_ids, verified_ranges):
        return [ValidationResult("steel_braces.csv")]

    monkeypatch.setattr(curation, "validate_all", fake_validate)


async def test_the_person_who_submitted_reads_their_own(monkeypatch, no_validation):
    """The edit step (#321) loads the submission through these endpoints."""
    use_client(monkeypatch, FakeClient())
    await _read_everything(make_request(OWNER))


@pytest.mark.parametrize("user", [STRANGER, None])
async def test_anyone_else_is_refused(monkeypatch, no_validation, user):
    use_client(monkeypatch, FakeClient())
    for call in (
        get_contribution(make_request(user), 7),
        get_contribution_validation(make_request(user), 7),
        get_contribution_comments(make_request(user), 7),
        get_contribution_file(make_request(user), 7, "braces/steel_braces.csv"),
    ):
        with pytest.raises(HTTPException) as caught:
            await call
        assert caught.value.status_code == 403


async def test_a_refusal_holds_when_the_answer_is_cached(monkeypatch, no_validation):
    """A curator fills the caches; a stranger must not read through them."""
    use_client(monkeypatch, FakeClient())
    await _read_everything(make_request(CURATOR))
    with pytest.raises(HTTPException) as caught:
        await get_contribution_validation(make_request(STRANGER), 7)
    assert caught.value.status_code == 403


async def test_the_owner_is_found_after_the_cache_dropped_it(monkeypatch):
    use_client(monkeypatch, FakeClient())
    await get_contribution(make_request(CURATOR), 7)
    curation._cache.drop(("owner", 7, "head-sha"))
    assert (await get_contribution(make_request(OWNER), 7)).mine is True


async def test_an_unknown_submitter_leaves_it_to_curators(monkeypatch):
    client = FakeClient(commits=[{"sha": "x", "message": "pushed by hand"}])
    client.texts[(PROVENANCE_PATH, "head-sha")] = "not json"
    use_client(monkeypatch, client)
    await get_contribution(make_request(CURATOR), 7)
    with pytest.raises(HTTPException) as caught:
        await get_contribution(make_request(OWNER), 7)
    assert caught.value.status_code == 403


# --- validation -------------------------------------------------------------


async def test_validation_rows_align_with_experiments(monkeypatch):
    client = FakeClient()
    use_client(monkeypatch, client)
    seen = {}

    def fake_validate(input_type, dirs, cpu, check_duplicate_ids, verified_ranges):
        with open(dirs[0] + "/braces/steel_braces.csv", encoding="utf-8") as file:
            seen["primary"] = file.read()
        seen["flags"] = (check_duplicate_ids, verified_ranges)
        result = ValidationResult("steel_braces.csv")
        result.file_path = dirs[0] + "/braces/steel_braces.csv"
        result.add_error(1, "f_y", "400", "Suspicious")
        return [result]

    monkeypatch.setattr(curation, "validate_all", fake_validate)
    response = await get_contribution_validation(make_request(), 7)
    # The temp CSV holds exactly the reconstructed batch, in experiments order:
    # issue row 1 is experiments[0].
    assert seen["primary"] == "id,f_y,name\nB9,400,New one\n"
    # A submission is new data: duplicate ids checked, ranges over every row.
    assert seen["flags"] == (True, False)
    assert response.valid is False
    assert response.results[0].errors[0].row == 1


async def test_validation_skips_oversized_curves(monkeypatch):
    client = FakeClient()
    client.texts[("braces/force_displacement/B9.csv", "head-sha")] = "x" * (
        curation.MAX_CURVE_FILE_BYTES + 1
    )
    use_client(monkeypatch, client)
    monkeypatch.setattr(
        curation, "validate_all", lambda *a, **k: [ValidationResult("steel_braces.csv")]
    )
    response = await get_contribution_validation(make_request(), 7)
    skipped = [
        r for r in response.results if r.path == "braces/force_displacement/B9.csv"
    ]
    assert len(skipped) == 1
    assert "too large" in skipped[0].warnings[0].message


# --- files ------------------------------------------------------------------


async def test_files_serves_only_submission_files(monkeypatch):
    use_client(monkeypatch, FakeClient())
    text = await get_contribution_file(
        make_request(), 7, "braces/force_displacement/B9.csv"
    )
    assert text == CURVE_CSV

    with pytest.raises(HTTPException) as caught:
        await get_contribution_file(
            make_request(), 7, "contributions/braces/abcd1234.json"
        )
    assert caught.value.status_code == 404

    with pytest.raises(HTTPException) as caught:
        await get_contribution_file(make_request(), 7, ".github/workflows/ci.yml")
    assert caught.value.status_code == 404


# --- comments ---------------------------------------------------------------


async def test_comments_open_with_the_pull_request_body(monkeypatch):
    use_client(monkeypatch, FakeClient())
    response = await get_contribution_comments(make_request(), 7)

    assert response.pr_number == 7
    assert len(response.items) == 3
    body = response.items[0]
    assert body.is_body is True
    assert body.id == 0
    assert body.author_type == "Bot"
    assert "Ada Lovelace" in body.body
    assert body.html_url == "https://github.com/x/pull/7"


async def test_comments_keep_github_order_and_fields(monkeypatch):
    use_client(monkeypatch, FakeClient())
    response = await get_contribution_comments(make_request(), 7)

    assert [item.id for item in response.items] == [0, 101, 102]
    assert [item.is_body for item in response.items] == [True, False, False]
    first = response.items[1]
    assert first.author == "dlignos"
    assert first.author_type == "User"
    assert first.body == "Could you confirm the coupon orientation?"
    assert first.html_url.endswith("#issuecomment-101")
    assert first.created_at == "2026-08-02T09:00:00+00:00"


async def test_comments_on_a_submission_with_no_replies(monkeypatch):
    use_client(monkeypatch, FakeClient(comments=[]))
    response = await get_contribution_comments(make_request(), 7)

    assert [item.is_body for item in response.items] == [True]


async def test_comments_cached_between_calls(monkeypatch):
    client = FakeClient()
    use_client(monkeypatch, client)
    await get_contribution_comments(make_request(), 7)
    await get_contribution_comments(make_request(), 7)

    assert client.comment_calls == 1


async def test_comments_404_on_closed_or_foreign_pull(monkeypatch):
    use_client(monkeypatch, FakeClient(pulls=[make_pull(state="closed")]))
    with pytest.raises(HTTPException) as caught:
        await get_contribution_comments(make_request(), 7)
    assert caught.value.status_code == 404

    monkeypatch.setattr(curation, "_cache", curation._TTLCache())
    use_client(
        monkeypatch,
        FakeClient(pulls=[make_pull(head_ref="feature/other")], files=TWO_DATABASES),
    )
    with pytest.raises(HTTPException) as caught:
        await get_contribution_comments(make_request(), 7)
    assert caught.value.status_code == 404
    assert "Changes 2 databases" in caught.value.detail


async def test_comments_502_when_github_fails(monkeypatch):
    class Failing(FakeClient):
        async def list_issue_comments(self, number):
            raise RuntimeError("boom")

    use_client(monkeypatch, Failing())
    with pytest.raises(HTTPException) as caught:
        await get_contribution_comments(make_request(), 7)
    assert caught.value.status_code == 502


async def test_invalidate_pull_forgets_a_submission(monkeypatch):
    """An update through the Hub must show at once, not a minute later.

    The detail and file caches are keyed by head sha and expire on their own,
    but the pull request itself and the queue are keyed by number, so an
    update would otherwise serve the head commit it just replaced.
    """
    client = FakeClient()
    use_client(monkeypatch, client)
    await list_contributions(make_request())
    first = await get_contribution(make_request(), 7)
    assert first.head_sha == "head-sha"

    moved = make_pull(head_sha="new-sha")
    client.pulls = [moved]
    client.texts[("braces/steel_braces.csv", "new-sha")] = HEAD_CSV
    client.texts[("contributions/braces/abcd1234.json", "new-sha")] = PROVENANCE

    assert (await get_contribution(make_request(), 7)).head_sha == "head-sha"  # cached
    curation.invalidate_pull(7)
    assert (await get_contribution(make_request(), 7)).head_sha == "new-sha"
    assert curation._cache.get("list") is None


async def test_a_hub_submission_drops_the_list_cache(monkeypatch):
    """A pull request opened by the Hub shows in the queue at once (#267)."""
    from resslab_hub.models.contribution import ContributionResponse
    from resslab_hub.routers import contributions as contributions_router

    async def opened(file, run):
        return ContributionResponse(
            pr_url="https://github.com/x/pull/12",
            pr_number=12,
            branch="contrib/braces/b9-abcd1234",
            head_sha="sha",
        )

    monkeypatch.setattr(contributions_router, "_run_on_archive", opened)
    monkeypatch.setattr(contributions_router, "_contributor", lambda user: CONTRIBUTOR)
    client = FakeClient()
    use_client(monkeypatch, client)
    await list_contributions(make_request())
    await contributions_router.create_contribution(
        request=make_request(),
        file=None,
        type=Type.ALL_BRACE,
        dismissed_warnings="[]",
        user=OWNER,
        _=None,
    )
    await list_contributions(make_request())
    assert client.list_calls == 2
