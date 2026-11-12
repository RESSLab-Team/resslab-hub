"""
Review 05: GitHub's limits against what one submission sends.

GitHub's documented secondary limits for content-creating requests are 80 per
minute and 500 per hour. A new submission sends one `create blob` per file
(the merged primary CSV plus every curve file), 8 at a time, then a tree, a
commit, a ref, a pull request and a review request.

githubkit retries a rate-limit answer once, after sleeping `retry_after`,
inside the request. The Hub keeps the default rule, so the sleep has no cap.
"""

from datetime import timedelta

import httpx
import pytest
from githubkit.exception import SecondaryRateLimitExceeded
from githubkit.response import Response

from resslab_hub.contributions import github
from resslab_hub.contributions.github import NewFile
from tests.test_github_client import FakeGit, client_with


class CountingGit(FakeGit):
    def __init__(self):
        super().__init__()
        self.refs: list = []

    async def async_create_ref(self, owner, repo, ref, sha):
        self.refs.append(ref)


@pytest.mark.xfail(strict=True, reason="review 05: 05-11")
async def test_a_large_batch_stays_under_the_per_minute_content_limit():
    git = CountingGit()
    # 40 specimens with 3 curve files each, plus the merged primary CSV.
    files = [NewFile("braces/steel_braces.csv", "id\n")] + [
        NewFile(f"connections/{kind}/C{n}.csv", f"{kind},{n}\n")
        for n in range(40)
        for kind in ("Global", "Panel_zone", "Beam")
    ]

    await client_with(git).commit_files(
        "contrib/x", "base-sha", files, "msg", "Ada", "ada@example.edu"
    )

    content_requests = len(git.blobs) + 1 + 1 + len(git.refs)  # tree, commit
    # Today: 121 blobs + tree + commit + ref = 124, sent in seconds.
    # Safe: the file contents go inline in the tree, or the uploads are paced.
    assert content_requests <= 80


def rate_limited(retry_after: timedelta) -> SecondaryRateLimitExceeded:
    request = httpx.Request("POST", "https://api.github.com/repos/x/y/git/blobs")
    raw = httpx.Response(
        403,
        headers={"retry-after": str(int(retry_after.total_seconds()))},
        json={"message": "You have exceeded a secondary rate limit."},
        request=request,
    )
    return SecondaryRateLimitExceeded(Response(raw, dict), retry_after)


@pytest.mark.xfail(strict=True, reason="review 05: 05-12")
def test_the_hub_does_not_sleep_for_an_hour_inside_a_request(monkeypatch):
    monkeypatch.setattr(github, "_shared_github", None)
    monkeypatch.setattr(github.settings, "github_app_id", "1")
    monkeypatch.setattr(github.settings, "github_app_private_key", "not-a-key")
    monkeypatch.setattr(github.settings, "github_app_installation_id", "1")

    retry = github._github().config.auto_retry
    decision = retry(rate_limited(timedelta(hours=1)), 0)

    # Today: retry after 3600 s, while the person waits on the submit and the
    # ingress gives up after 5 minutes. Safe: fail at once, or wait seconds.
    assert not decision.do_retry or decision.retry_after <= timedelta(seconds=30)
