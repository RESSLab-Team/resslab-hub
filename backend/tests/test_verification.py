"""
Verification pull requests (#253).

The pull request itself is built against a fake GitHub client, like the
submissions in ``test_contributions.py``. The role gates and the list from the
database go over HTTP, through the ``client`` fixture.
"""

import pytest

from resslab_hub.contributions.projection import SubmissionError
from resslab_hub.contributions.submission import Contributor
from resslab_hub.contributions.trailers import parse_trailers
from resslab_hub.contributions.verification import (
    build_verification_body,
    clean_ids,
    ids_from_body,
    open_verification,
    pending_verifications,
    read_live_batch,
    type_for_verify_branch,
)
from resslab_hub.data.uploader import Type, upload_one
from resslab_hub.models.database.brace import Brace
from resslab_hub.routers import verification as verification_router
from resslab_hub.routers.verification import group_unverified
from resslab_hub.utils.rate_limit import limiter
from tests.conftest import github_refusal, write_main_csv

CURATOR = Contributor(name="Dimitrios Lignos", email="dimitrios@example.edu")
PATH = "braces/steel_braces.csv"
REPO_CSV = (
    "id,f_y,reference,data_curation_status\r\n"
    "B1,355,Ref A,verified\r\n"
    "B2,275,Ref A,unverified\r\n"
    '"B3",300,"Ref, B",unverified\r\n'
)


class FakeClient:
    """In-memory DataRepoClient double recording every call."""

    def __init__(self, repo_files: dict, folders: dict = None):
        self.repo_files = repo_files
        self.folders = folders or {}
        self.read_refs: list = []
        self.committed: list = []
        self.commit_kwargs: dict = {}
        self.pr: dict = {}
        self.deleted_branches: list = []
        self.fail_pr = False
        self.reviewers: list = []

    async def get_base_sha(self):
        return "base-sha"

    async def get_file_text(self, path, ref=None):
        self.read_refs.append(ref)
        return self.repo_files[path]

    async def list_dir(self, path, ref=None):
        self.read_refs.append(ref)
        return self.folders.get(path, [])

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
        return {"url": "https://github.com/x/pull/9", "number": 9}

    async def delete_branch(self, branch):
        self.deleted_branches.append(branch)

    async def list_admin_logins(self):
        return ["dlignos", "andskia"]

    async def request_reviewers(self, number, logins):
        self.reviewers = logins


async def verify(ids, client, pending=None):
    return await open_verification(
        Type.ALL_BRACE, ids, CURATOR, pending=pending, client=client
    )


# --- the pull request --------------------------------------------------------
async def test_only_the_status_cells_change():
    client = FakeClient({PATH: REPO_CSV})

    result = await verify(["B2"], client)

    assert result.pr_number == 9
    content = {f.path: f.content for f in client.committed}[PATH]
    # CRLF kept, the quoted id left as the csv module writes it, one cell moved.
    assert content == REPO_CSV.replace(
        "B2,275,Ref A,unverified", "B2,275,Ref A,verified"
    ).replace('"B3"', "B3")


async def test_a_bom_is_kept():
    client = FakeClient({PATH: "\ufeffid,data_curation_status\nB1,unverified\n"})

    await verify(["B1"], client)

    assert client.committed[0].content == "\ufeffid,data_curation_status\nB1,verified\n"


async def test_the_file_is_read_at_the_commit_the_branch_starts_from():
    client = FakeClient({PATH: REPO_CSV})

    await verify(["B2"], client)

    assert client.read_refs == ["base-sha"]
    assert client.commit_kwargs["base_sha"] == "base-sha"


async def test_branch_title_and_trailer():
    client = FakeClient({PATH: REPO_CSV})

    result = await verify(["B2", "B3"], client)

    assert result.branch.startswith("verify/braces/b2-")
    assert client.pr["title"] == "data(braces): verify 2 experiments (B2…)"
    message = client.commit_kwargs["message"]
    assert message.startswith(client.pr["title"] + "\n\n")
    trailers = parse_trailers(message)
    assert trailers["Verified-by"] == ["Dimitrios Lignos <dimitrios@example.edu>"]
    # Not a submission: nothing may read it as one.
    assert "Submitted-by" not in trailers
    assert client.commit_kwargs["author_name"] == "Dimitrios Lignos"
    assert client.commit_kwargs["author_email"] == "dimitrios@example.edu"
    assert ids_from_body(client.pr["body"]) == ["B2", "B3"]


async def test_the_admins_are_asked_but_not_the_curator(monkeypatch):
    """A verification needs an approval too (#266)."""
    from resslab_hub.config import settings

    monkeypatch.setattr(settings, "data_repo_reviewers", "admins")
    client = FakeClient({PATH: REPO_CSV})
    curator = Contributor(
        name="Dimitrios Lignos", email="dimitrios@example.edu", github_login="dlignos"
    )

    await open_verification(Type.ALL_BRACE, ["B2"], curator, client=client)

    assert client.reviewers == ["andskia"]


async def test_unknown_ids_are_refused():
    client = FakeClient({PATH: REPO_CSV})

    with pytest.raises(SubmissionError) as caught:
        await verify(["B2", "B404"], client)

    assert caught.value.status_code == 409
    assert "B404" in caught.value.detail
    assert client.committed == []


async def test_ids_already_verified_are_refused():
    client = FakeClient({PATH: REPO_CSV})

    with pytest.raises(SubmissionError) as caught:
        await verify(["B1", "B2"], client)

    assert caught.value.status_code == 409
    assert "already verified" in caught.value.detail
    assert "B1" in caught.value.detail
    assert client.committed == []


async def test_ids_in_an_open_verification_are_refused():
    client = FakeClient({PATH: REPO_CSV})
    pending = pending_verifications(
        [
            {
                "number": 5,
                "html_url": "https://github.com/x/pull/5",
                "head_ref": "verify/braces/b2-abcd1234",
                "body": build_verification_body(CURATOR, Type.ALL_BRACE, ["B2"], PATH),
            }
        ]
    )

    with pytest.raises(SubmissionError) as caught:
        await verify(["B2"], client, pending=pending)

    assert caught.value.status_code == 409
    assert "B2 (#5)" in caught.value.detail


async def test_a_repo_without_the_column_is_refused():
    client = FakeClient({PATH: "id,f_y\nB1,355\n"})

    with pytest.raises(SubmissionError) as caught:
        await verify(["B1"], client)

    assert caught.value.status_code == 502


async def test_no_ids_and_too_many_ids_are_refused():
    client = FakeClient({PATH: REPO_CSV})
    for ids in ([], ["  "], [f"B{n}" for n in range(501)]):
        with pytest.raises(SubmissionError) as caught:
            await verify(ids, client)
        assert caught.value.status_code == 400


async def test_the_branch_is_deleted_when_the_pull_request_fails():
    client = FakeClient({PATH: REPO_CSV})
    client.fail_pr = True

    with pytest.raises(SubmissionError) as caught:
        await verify(["B2"], client)

    assert caught.value.status_code == 502
    assert client.deleted_branches == [client.commit_kwargs["branch"]]


# --- reading pull requests back ---------------------------------------------
# --- the live batch the review page shows -----------------------------------
async def test_the_live_batch_reads_the_rows_and_their_curves():
    curves = "braces/force_displacement"
    client = FakeClient(
        {PATH: REPO_CSV},
        # B1 is verified and not asked for, notes.txt is not a curve.
        {curves: ["B1.csv", "B2.csv", "B3.csv", "notes.txt"]},
    )

    batch = await read_live_batch(client, Type.ALL_BRACE, ["B3", "B2", "B9"], "sha")

    # CSV order, every cell kept as text, the quoted id unquoted.
    assert [experiment.id for experiment in batch.experiments] == ["B2", "B3"]
    assert batch.experiments[1].cells == {
        "id": "B3",
        "f_y": "300",
        "reference": "Ref, B",
        "data_curation_status": "unverified",
    }
    assert batch.columns == ["id", "f_y", "reference", "data_curation_status"]
    assert [(file.path, file.experiment_id) for file in batch.files] == [
        (f"{curves}/B2.csv", "B2"),
        (f"{curves}/B3.csv", "B3"),
    ]
    assert batch.missing_ids == ["B9"]
    # Everything at the commit the page was given, never the moving branch.
    assert set(client.read_refs) == {"sha"}


def test_clean_ids_strips_blanks_and_repeats():
    assert clean_ids([" B2", "B2", "", "B1 "]) == ["B2", "B1"]


def test_type_for_verify_branch():
    assert type_for_verify_branch("verify/braces/b2-abcd") is Type.ALL_BRACE
    assert type_for_verify_branch("verify/nope/b2-abcd") is None
    assert type_for_verify_branch("contrib/braces/b2-abcd") is None


def test_pending_ignores_submissions_and_bodies_without_ids():
    pulls = [
        {"number": 1, "head_ref": "contrib/braces/b9-abcd", "body": "```ids\nB9\n```"},
        {"number": 2, "head_ref": "verify/braces/b2-abcd", "body": "edited by hand"},
        {"number": 3, "head_ref": "verify/columns/c1-abcd", "body": "```ids\nC1\n```"},
    ]

    pending = pending_verifications(pulls)

    assert list(pending) == [(Type.ALL_COLUMN, "C1")]


def test_groups_by_database_and_reference():
    rows = [
        (Type.ALL_COLUMN, "C1", "Ref Z"),
        (Type.ALL_BRACE, "B3", "Ref B"),
        (Type.ALL_BRACE, "B2", "Ref A"),
        (Type.ALL_BRACE, "B1", "Ref A"),
        (Type.ALL_BRACE, "B4", None),
    ]

    groups = group_unverified(rows, {})

    assert [(g.database, g.reference, g.ids) for g in groups] == [
        ("all-braces", "", ["B4"]),
        ("all-braces", "Ref A", ["B1", "B2"]),
        ("all-braces", "Ref B", ["B3"]),
        ("all-columns", "Ref Z", ["C1"]),
    ]
    assert groups[1].count == 2
    assert all(g.pending_pr is None for g in groups)


def test_rows_in_an_open_verification_get_their_own_group():
    pull = {"number": 5, "html_url": "https://github.com/x/pull/5"}
    rows = [(Type.ALL_BRACE, "B1", "Ref A"), (Type.ALL_BRACE, "B2", "Ref A")]

    groups = group_unverified(rows, {(Type.ALL_BRACE, "B1"): pull})

    assert [(g.ids, g.pending_pr and g.pending_pr.pr_number) for g in groups] == [
        (["B2"], None),
        (["B1"], 5),
    ]


# --- over HTTP ---------------------------------------------------------------
@pytest.fixture
def _no_rate_limits(monkeypatch):
    monkeypatch.setattr(limiter, "enabled", False)


async def test_the_routes_need_a_curator(client, sign_in, _no_rate_limits):
    body = {"database": "all-braces", "ids": ["B1"]}
    assert (await client.get("/verification")).status_code == 401
    sign_in(role="contributor")
    assert (await client.get("/verification")).status_code == 403
    assert (await client.post("/verification", json=body)).status_code == 403


async def test_the_list_comes_from_the_database(
    client, sign_in, tmp_path, monkeypatch, _no_rate_limits
):
    monkeypatch.setattr(verification_router, "configured", lambda: False)
    csv_path = tmp_path / "steel_braces.csv"
    write_main_csv(
        csv_path,
        Brace,
        [
            {"id": "B1", "reference": "Ref A", "data_curation_status": "unverified"},
            {"id": "B2", "reference": "Ref A", "data_curation_status": "unverified"},
            {"id": "B3", "reference": "Ref A"},
        ],
    )
    upload_one(Type.BRACE, str(csv_path))
    sign_in(role="curator")

    response = await client.get("/verification")

    assert response.status_code == 200
    assert response.json() == {
        "configured": False,
        "groups": [
            {
                "database": "all-braces",
                "reference": "Ref A",
                "ids": ["B1", "B2"],
                "count": 2,
                "pending_pr": None,
            }
        ],
    }
    # Per signed-in user: the shared response cache must never keep it.
    assert "public" not in response.headers.get("cache-control", "")


async def test_a_type_without_a_status_is_refused(
    client, sign_in, monkeypatch, _no_rate_limits
):
    monkeypatch.setattr(verification_router, "configured", lambda: True)
    sign_in(role="curator")

    response = await client.post(
        "/verification", json={"database": "brace-displacement", "ids": ["B1"]}
    )

    assert response.status_code == 400


async def test_a_github_refusal_says_why(client, sign_in, monkeypatch, _no_rate_limits):
    fake = FakeClient({PATH: REPO_CSV})

    async def refuse(*args, **kwargs):
        raise github_refusal(403, {"message": "Resource not accessible by integration"})

    async def no_pulls(client):
        return []

    fake.commit_files = refuse
    monkeypatch.setattr(verification_router, "configured", lambda: True)
    monkeypatch.setattr(verification_router, "DataRepoClient", lambda: fake)
    monkeypatch.setattr(verification_router, "open_pulls", no_pulls)
    sign_in(role="curator")

    response = await client.post(
        "/verification", json={"database": "all-braces", "ids": ["B2"]}
    )

    # GitHub failed, not the Hub: a 502 that names the reason, not a bare 500.
    assert response.status_code == 502
    assert response.json() == {
        "detail": "GitHub answered 403: Resource not accessible by integration"
    }


async def test_the_review_routes_need_a_curator(client, sign_in, _no_rate_limits):
    sign_in(role="contributor")
    for route in ("batch", "validation"):
        response = await client.get(f"/verification/all-braces/{route}?reference=A")
        assert response.status_code == 403
    response = await client.get(
        "/verification/all-braces/files", params={"path": "x", "ref": "y"}
    )
    assert response.status_code == 403


async def test_the_batch_is_the_unverified_rows_of_one_reference(
    client, sign_in, tmp_path, monkeypatch, _no_rate_limits
):
    monkeypatch.setattr(verification_router, "configured", lambda: True)
    monkeypatch.setattr(verification_router, "_cache", verification_router._TTLCache())
    fake = FakeClient({PATH: REPO_CSV}, {"braces/force_displacement": ["B2.csv"]})
    monkeypatch.setattr(verification_router, "DataRepoClient", lambda: fake)
    monkeypatch.setattr(verification_router, "open_pulls", _open_verification_pull)
    csv_path = tmp_path / "steel_braces.csv"
    write_main_csv(
        csv_path,
        Brace,
        [
            {"id": "B1", "reference": "Ref A"},
            {"id": "B2", "reference": "Ref A", "data_curation_status": "unverified"},
            {"id": "B3", "reference": "Ref, B", "data_curation_status": "unverified"},
        ],
    )
    upload_one(Type.BRACE, str(csv_path))
    sign_in(role="curator")

    response = await client.get(
        "/verification/all-braces/batch", params={"reference": "Ref A"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["base_sha"] == "base-sha"
    assert [experiment["id"] for experiment in body["experiments"]] == ["B2"]
    assert [file["path"] for file in body["files"]] == [
        "braces/force_displacement/B2.csv"
    ]
    assert body["missing_ids"] == []
    assert body["pending"] == {
        "B2": {"pr_number": 12, "pr_url": "https://github.com/x/pull/12"}
    }
    assert "public" not in response.headers.get("cache-control", "")

    missing = await client.get(
        "/verification/all-braces/batch", params={"reference": "Ref C"}
    )
    assert missing.status_code == 404


async def test_the_checks_do_not_flag_the_rows_as_already_there(
    client, sign_in, tmp_path, monkeypatch, _no_rate_limits
):
    # The rows under review are in the database on purpose: the duplicate id
    # check of a submission would flag every one of them.
    monkeypatch.setattr(verification_router, "configured", lambda: True)
    monkeypatch.setattr(verification_router, "_cache", verification_router._TTLCache())
    fake = FakeClient({PATH: REPO_CSV})
    monkeypatch.setattr(verification_router, "DataRepoClient", lambda: fake)
    monkeypatch.setattr(verification_router, "open_pulls", _open_verification_pull)
    csv_path = tmp_path / "steel_braces.csv"
    write_main_csv(
        csv_path,
        Brace,
        [{"id": "B2", "reference": "Ref A", "data_curation_status": "unverified"}],
    )
    upload_one(Type.BRACE, str(csv_path))
    sign_in(role="curator")

    response = await client.get(
        "/verification/all-braces/validation", params={"reference": "Ref A"}
    )

    assert response.status_code == 200
    messages = [
        issue["message"]
        for result in response.json()["results"]
        for issue in result["errors"] + result["warnings"]
    ]
    assert not [message for message in messages if "already exists" in message]


async def test_the_files_route_only_serves_curves(
    client, sign_in, monkeypatch, _no_rate_limits
):
    monkeypatch.setattr(verification_router, "configured", lambda: True)
    monkeypatch.setattr(verification_router, "_cache", verification_router._TTLCache())
    curve = "braces/force_displacement/B2.csv"
    fake = FakeClient({curve: "d,f\n0,0\n", PATH: REPO_CSV})
    monkeypatch.setattr(verification_router, "DataRepoClient", lambda: fake)
    sign_in(role="curator")
    sha = "a" * 40

    ok = await client.get(
        "/verification/all-braces/files", params={"path": curve, "ref": sha}
    )
    assert ok.status_code == 200
    assert ok.text == "d,f\n0,0\n"
    assert fake.read_refs == [sha]

    for path, ref in ((PATH, sha), ("../secrets/.env", sha), (curve, "main")):
        refused = await client.get(
            "/verification/all-braces/files", params={"path": path, "ref": ref}
        )
        assert refused.status_code == 404


async def _open_verification_pull(_client):
    return [
        {
            "number": 12,
            "html_url": "https://github.com/x/pull/12",
            "head_ref": "verify/braces/b2-abcd",
            "body": "```ids\nB2\n```",
        }
    ]
