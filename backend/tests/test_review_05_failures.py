"""
Review 05: what is left on GitHub, and what the person reads, when a step of
a submission or an edit fails half way.
"""

import asyncio
import logging

import httpx
import pytest
from githubkit.exception import RequestTimeout

from resslab_hub.contributions.github import describe_error
from resslab_hub.contributions.submission import SubmissionError, submit_contribution
from resslab_hub.data.uploader import Type
from tests.test_contributions import (
    CONTRIBUTOR,
    REPO_CSV,
    FakeClient,
    edit_client,
    make_batch,
    patch_validation,
    update,
)
from tests.test_github_client import FakeGit, client_with


class LostAnswerClient(FakeClient):
    """GitHub opens the pull request, but the answer never comes back.

    githubkit retries a 5xx up to three times. A POST that GitHub did run but
    answered 502 comes back, on the retry, as 422 "A pull request already
    exists". Either way the Hub sees an exception after the PR exists.
    """

    async def create_pull_request(self, branch, title, body):
        self.pr = {"branch": branch, "title": title, "body": body}
        raise RuntimeError("A pull request already exists for x:" + branch)


@pytest.mark.xfail(strict=True, reason="review 05: 05-6")
async def test_a_pull_request_that_exists_is_not_closed_by_the_cleanup(
    tmp_path, monkeypatch
):
    patch_validation(monkeypatch)
    client = LostAnswerClient({"braces/steel_braces.csv": REPO_CSV})

    with pytest.raises(SubmissionError):
        await submit_contribution(
            str(make_batch(tmp_path)), Type.ALL_BRACE, CONTRIBUTOR, [], client=client
        )

    # The pull request is open on GitHub. Deleting its branch closes it, and a
    # closed pull request with the name and address stays public for good.
    # Safe: look for the pull request first, keep the branch when it exists.
    assert client.deleted_branches == []


async def test_a_failed_branch_cleanup_is_logged(caplog):
    class RefusingGit(FakeGit):
        async def async_delete_ref(self, owner, repo, ref):
            raise RuntimeError("Resource not accessible by integration")

    client = client_with(RefusingGit())

    with caplog.at_level(logging.DEBUG):
        await client.delete_branch("contrib/braces/b9-abcd1234")

    # Safe: someone can learn that a branch with a name and an address is
    # still on the public repository.
    assert "contrib/braces/b9-abcd1234" in caplog.text


@pytest.mark.xfail(strict=True, reason="review 05: 05-8")
async def test_a_timeout_on_the_edit_commit_is_not_called_a_moved_branch(
    tmp_path, monkeypatch
):
    patch_validation(monkeypatch)
    client = edit_client()

    async def timeout(*args, **kwargs):
        raise RequestTimeout(httpx.ReadTimeout("timed out"))

    client.commit_on_branch = timeout

    with pytest.raises(SubmissionError) as caught:
        await update(make_batch(tmp_path, "id,f_y,name\nB9,450,Fixed one\n"), client)

    # Today: 409 "its branch moved on GitHub. Reload the page and make your
    # changes again." The branch did not move: the person reloads, redoes the
    # work, and hits the same timeout. Safe: a 502/504 that says GitHub did
    # not answer.
    assert caught.value.status_code != 409
    assert "moved" not in caught.value.detail


@pytest.mark.xfail(strict=True, reason="review 05: 05-9")
async def test_a_github_timeout_is_described_in_words():
    # A real read timeout, as httpx raises it in async code: a local server
    # that accepts the connection and never answers.
    async def silent(reader, writer):
        await asyncio.sleep(5)

    server = await asyncio.start_server(silent, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    async with httpx.AsyncClient(timeout=0.2) as http:
        with pytest.raises(httpx.ReadTimeout) as caught:
            await http.get(f"http://127.0.0.1:{port}/")
    server.close()

    # httpcore maps anyio's bare TimeoutError, so the text is empty, and the
    # submit answers "The pull request could not be opened on the data
    # repository ()." Safe: words that say GitHub did not answer in time.
    assert describe_error(RequestTimeout(caught.value)) != ""


@pytest.mark.xfail(strict=True, reason="review 05: 05-10")
async def test_an_edit_with_no_file_change_keeps_body_and_trailers_in_step(
    tmp_path, monkeypatch
):
    """Same files, new dismissed warnings: no commit, but a new body."""
    patch_validation(monkeypatch)
    client = edit_client()

    async def no_change(branch, head_sha, *args, **kwargs):
        # What DataRepoClient.commit_on_branch answers when every blob sha
        # matches the branch head (github.py, `commit_sha == head_sha`).
        return head_sha

    client.commit_on_branch = no_change

    await update(
        make_batch(tmp_path, "id,f_y,name\nB9,450,Fixed one\n"),
        client,
        dismissed=["B9: f_y far outside the existing range"],
    )

    # The body now lists a dismissed warning that no commit trailer holds, so
    # it is lost at the squash merge. Safe: no body change without a commit.
    assert "far outside" not in client.pr.get("body", "")
