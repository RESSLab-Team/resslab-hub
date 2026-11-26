"""
Tests for the data-repo GitHub client itself (contributions/github.py).

Two things this pins, both of which cost a contribution edit tens of seconds
before: the httpx client is shared between calls instead of rebuilt (and its
TLS handshake redone) per call, and a commit only uploads the files whose
content actually changed.
"""

import asyncio
from types import SimpleNamespace

import httpx
import pytest

from resslab_hub.contributions.github import (
    DataRepoClient,
    NewFile,
    _SharedGitHub,
    blob_sha,
    describe_error,
    public_error,
)
from tests.conftest import github_refusal


def test_blob_sha_matches_git_hash_object():
    # `git hash-object` on this exact content answers the same digest.
    text = "Displacement [mm],Force [kN]\n0,0\n"
    assert blob_sha(text) == "756abe06d82b296c3007cfe33952672ca87847cc"


def _bare_shared_github(factory) -> _SharedGitHub:
    github = _SharedGitHub.__new__(_SharedGitHub)
    github._shared_client = None
    github._client_lock = asyncio.Lock()
    github._create_async_client = factory
    return github


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "is_async", [False, True], ids=["sync factory", "async factory"]
)
async def test_shared_client_is_built_once_and_stays_open(is_async):
    """githubkit closes its client after every call; ours must not.

    githubkit 0.12 builds its client with a sync method, 0.17 with a
    coroutine. Both must work.
    """
    closed = []
    built = []

    class FakeAsyncClient:
        async def aclose(self):
            closed.append(self)

    if is_async:

        async def factory():
            await asyncio.sleep(0)
            built.append(FakeAsyncClient())
            return built[-1]

    else:

        def factory():
            built.append(FakeAsyncClient())
            return built[-1]

    github = _bare_shared_github(factory)

    async with github.get_async_client() as first:
        pass
    async with github.get_async_client() as second:
        pass

    assert first is second
    assert len(built) == 1
    # Still usable after both calls: no aclose() in between.
    assert closed == []

    await github.aclose()
    assert closed == [first]


@pytest.mark.asyncio
async def test_two_first_calls_at_once_build_one_client():
    built = []

    async def factory():
        await asyncio.sleep(0.01)
        built.append(object())
        return built[-1]

    github = _bare_shared_github(factory)

    async def use():
        async with github.get_async_client() as client:
            return client

    clients = await asyncio.gather(use(), use(), use())

    assert len(built) == 1
    assert clients[0] is clients[1] is clients[2]


@pytest.mark.asyncio
async def test_a_slow_call_times_out_and_the_client_is_reused():
    """A real local server that never answers: the call must fail fast.

    githubkit's default cache client ignored the timeout once (hishel 1.x),
    so this goes through the real client, not a fake.
    """
    from githubkit.exception import RequestTimeout

    async def never_answer(reader, writer):
        await reader.read(1)
        await asyncio.sleep(5)
        writer.close()

    server = await asyncio.start_server(never_answer, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    github = _SharedGitHub(
        "token", base_url=f"http://127.0.0.1:{port}", timeout=0.3, http_cache=False
    )
    loop = asyncio.get_running_loop()
    started = loop.time()
    try:
        with pytest.raises(RequestTimeout) as caught:
            await github.arequest("GET", "/slow")
        assert loop.time() - started < 3
        assert public_error(caught.value) == "GitHub did not answer in time"
        # The client survived the failure and is the one kept for next time.
        assert github._shared_client is not None
    finally:
        await github.aclose()
        server.close()


def test_the_process_client_has_our_timeout_and_no_cache(monkeypatch):
    from resslab_hub.contributions import github as module

    monkeypatch.setattr(module, "_shared_github", None)
    monkeypatch.setattr(module.settings, "github_app_id", "1", raising=False)
    monkeypatch.setattr(
        module.settings, "github_app_installation_id", "2", raising=False
    )
    monkeypatch.setattr(
        module.settings, "github_app_private_key", "not a real key", raising=False
    )
    client = module._github()
    assert client.config.timeout.read == module.REQUEST_TIMEOUT
    assert client.config.http_cache is False


class FakeGit:
    """The three Git Data calls a commit makes, counting blob uploads."""

    def __init__(self):
        self.blobs: list = []
        self.tree: list = []
        self.in_flight = 0
        self.max_in_flight = 0

    async def async_create_blob(self, owner, repo, content, encoding):
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            # Yield so overlapping uploads really do overlap.
            await asyncio.sleep(0)
            self.blobs.append(content)
            return SimpleNamespace(parsed_data=SimpleNamespace(sha=blob_sha(content)))
        finally:
            self.in_flight -= 1

    async def async_create_tree(self, owner, repo, base_tree, tree):
        self.tree = tree
        return SimpleNamespace(parsed_data=SimpleNamespace(sha="tree-sha"))

    async def async_create_commit(self, owner, repo, message, tree, parents, author):
        return SimpleNamespace(parsed_data=SimpleNamespace(sha="commit-sha"))


def client_with(git: FakeGit) -> DataRepoClient:
    """A DataRepoClient wired to `git`, with no settings and no network."""
    client = DataRepoClient.__new__(DataRepoClient)
    client.owner, client.repo = "RESSLab-Team", "resslab-hub-data"
    client.base_branch = "main"
    client._gh = SimpleNamespace(rest=SimpleNamespace(git=git))
    return client


@pytest.mark.asyncio
async def test_commit_uploads_every_file_when_nothing_is_known():
    """A new submission has no branch yet: everything goes up."""
    git = FakeGit()
    files = [NewFile("a.csv", "one\n"), NewFile("b.csv", "two\n")]

    sha = await client_with(git)._create_commit(
        "parent", files, [], "msg", "Ada", "ada@example.edu"
    )

    assert sha == "commit-sha"
    assert sorted(git.blobs) == ["one\n", "two\n"]
    assert [entry["path"] for entry in git.tree] == ["a.csv", "b.csv"]


@pytest.mark.asyncio
async def test_commit_skips_files_already_on_the_branch():
    """The curves an edit did not touch cost no upload and no tree entry."""
    git = FakeGit()
    files = [
        NewFile("braces/steel_braces.csv", "id,f_y\nB9,450\n"),  # edited
        NewFile("braces/force_displacement/B9.csv", "0,0\n"),  # untouched
    ]
    existing = {
        "braces/steel_braces.csv": blob_sha("id,f_y\nB9,400\n"),
        "braces/force_displacement/B9.csv": blob_sha("0,0\n"),
    }

    await client_with(git)._create_commit(
        "parent", files, [], "msg", "Ada", "ada@example.edu", existing=existing
    )

    assert git.blobs == ["id,f_y\nB9,450\n"]
    # The untouched curve stays out of the tree: base_tree already carries it.
    assert [entry["path"] for entry in git.tree] == ["braces/steel_braces.csv"]


@pytest.mark.asyncio
async def test_commit_uploads_blobs_in_parallel():
    git = FakeGit()
    files = [NewFile(f"c{n}.csv", f"{n}\n") for n in range(6)]

    await client_with(git)._create_commit(
        "parent", files, [], "msg", "Ada", "ada@example.edu"
    )

    assert len(git.blobs) == 6
    assert git.max_in_flight > 1


@pytest.mark.asyncio
async def test_commit_keeps_deletions_after_the_uploads():
    git = FakeGit()
    files = [NewFile("a.csv", "one\n")]

    await client_with(git)._create_commit(
        "parent", files, ["gone.csv"], "msg", "Ada", "ada@example.edu"
    )

    assert git.tree == [
        {"path": "a.csv", "mode": "100644", "type": "blob", "sha": blob_sha("one\n")},
        {"path": "gone.csv", "mode": "100644", "type": "blob", "sha": None},
    ]


@pytest.mark.asyncio
async def test_commit_with_nothing_to_write_answers_the_parent():
    """GitHub rejects an empty tree, and an empty commit is not worth making."""
    git = FakeGit()
    files = [NewFile("a.csv", "one\n")]
    existing = {"a.csv": blob_sha("one\n")}

    sha = await client_with(git)._create_commit(
        "parent", files, [], "msg", "Ada", "ada@example.edu", existing=existing
    )

    assert sha == "parent"
    assert git.blobs == []
    assert git.tree == []


def test_a_github_refusal_gives_github_reason():
    body = {"message": "Resource not accessible by integration", "status": "403"}

    assert describe_error(github_refusal(403, body)) == (
        "GitHub answered 403: Resource not accessible by integration"
    )


def test_the_field_errors_follow_the_message():
    body = {
        "message": "Validation Failed",
        "errors": [
            {"resource": "PullRequest", "code": "custom", "message": "A PR exists"},
            {"resource": "PullRequest", "field": "head", "code": "invalid"},
        ],
    }

    assert describe_error(github_refusal(422, body)) == (
        "GitHub answered 422: Validation Failed; A PR exists; invalid"
    )


def test_a_body_that_is_not_json_falls_back_on_the_status():
    refusal = github_refusal(502, "<html>Bad gateway</html>")

    assert describe_error(refusal) == "GitHub answered 502: Bad Gateway"


def test_any_other_error_keeps_its_text():
    assert describe_error(RuntimeError("boom")) == "boom"


def test_the_browser_gets_github_reason_but_not_our_own_errors(caplog):
    body = {"message": "Resource not accessible by integration"}
    assert public_error(github_refusal(403, body)) == (
        "GitHub answered 403: Resource not accessible by integration"
    )

    # Our own errors can carry paths or internal details (#264, H3): they go
    # to the logs, the browser gets a fixed sentence.
    secret = RuntimeError("could not open /app/secrets/key.pem")
    assert "secrets" not in public_error(secret)
    assert "/app/secrets/key.pem" in caplog.text

    assert public_error(httpx.ReadTimeout("read timed out")) == (
        "GitHub did not answer in time"
    )


@pytest.mark.asyncio
async def test_reviewers_are_the_admins_and_go_in_one_request():
    """#266: list the admins, then one review request with their logins."""
    calls: dict = {}

    async def list_collaborators(owner, repo, **params):
        calls["list"] = params
        users = [SimpleNamespace(login="dlignos"), SimpleNamespace(login="andskia")]
        return SimpleNamespace(parsed_data=users)

    async def request_reviewers(owner, repo, number, data):
        calls["request"] = (number, data)

    client = client_with(FakeGit())
    client._gh = SimpleNamespace(
        rest=SimpleNamespace(
            repos=SimpleNamespace(async_list_collaborators=list_collaborators),
            pulls=SimpleNamespace(async_request_reviewers=request_reviewers),
        )
    )

    logins = await client.list_admin_logins()
    await client.request_reviewers(7, logins)
    await client.request_reviewers(8, [])  # nothing to ask: no call

    assert calls["list"]["permission"] == "admin"
    assert calls["request"] == (7, {"reviewers": ["dlignos", "andskia"]})
