"""
Tests for the data-repo GitHub client itself (contributions/github.py).

Two things this pins, both of which cost a contribution edit tens of seconds
before: the httpx client is shared between calls instead of rebuilt (and its
TLS handshake redone) per call, and a commit only uploads the files whose
content actually changed.
"""

import asyncio
from types import SimpleNamespace

import pytest

from resslab_hub.contributions.github import (
    DataRepoClient,
    NewFile,
    _SharedGitHub,
    blob_sha,
)


def test_blob_sha_matches_git_hash_object():
    # `git hash-object` on this exact content answers the same digest.
    text = "Displacement [mm],Force [kN]\n0,0\n"
    assert blob_sha(text) == "756abe06d82b296c3007cfe33952672ca87847cc"


@pytest.mark.asyncio
async def test_shared_client_is_built_once_and_stays_open():
    """githubkit closes its client after every call; ours must not."""
    closed = []

    class FakeAsyncClient:
        async def aclose(self):
            closed.append(self)

    github = _SharedGitHub.__new__(_SharedGitHub)
    github._shared_client = None
    built = []
    github._create_async_client = lambda: built.append(FakeAsyncClient()) or built[-1]

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
