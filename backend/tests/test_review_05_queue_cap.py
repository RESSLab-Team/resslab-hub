"""
Review 05: the cap on open submissions (#264 H4).

`_check_queue_capacity` counts every open pull request whose head branch
starts with `contrib/`. A pull request from a fork counts too, and anyone with
a GitHub account can open one on the public data repo.
"""

import pytest

from resslab_hub.routers import contributions


def fork_pull(number: int) -> dict:
    return {
        "number": number,
        "head_ref": f"contrib/braces/spam-{number}",
        "head_repo": "someone/resslab-hub-data",
        "draft": False,
    }


@pytest.mark.xfail(strict=True, reason="review 05: 05-5")
async def test_pull_requests_from_forks_do_not_fill_the_queue(monkeypatch):
    async def open_pulls(_client):
        return [fork_pull(n) for n in range(1, 31)]

    monkeypatch.setattr(contributions, "configured", lambda: True)
    monkeypatch.setattr(contributions, "DataRepoClient", lambda: None)
    monkeypatch.setattr(contributions, "open_pulls", open_pulls)

    # Safe: 30 fork pull requests do not block a researcher's submission.
    await contributions._check_queue_capacity()
