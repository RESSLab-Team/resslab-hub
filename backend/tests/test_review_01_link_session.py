"""
Review 01, 01-6: the link callbacks never read the session.

``GET /auth/{github,orcid}/start?link=true`` stores the signed-in user in the
state row. The callback attaches the identity to that user, even when the
browser signed out in between. See docs/review/findings/01-sign-in.md.
"""

from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import select

from resslab_hub.auth import github_oauth, orcid_oauth
from resslab_hub.models.database.auth import Identity
from resslab_hub.utils.rate_limit import limiter

REASON = "review 01: 01-6"


@pytest.fixture(autouse=True)
def _no_rate_limits(monkeypatch):
    monkeypatch.setattr(limiter, "enabled", False)


@pytest.fixture
def github(monkeypatch):
    """GitHub on, with the profile call faked. Nothing leaves the process."""
    monkeypatch.setattr(github_oauth.settings, "github_oauth_client_id", "cid")
    monkeypatch.setattr(github_oauth.settings, "github_oauth_client_secret", "secret")
    profile = github_oauth.GitHubProfile(
        subject="4242",
        login="ada",
        name="Ada Lovelace",
        email="ada@example.edu",
        email_verified=True,
    )

    async def _fetch(code):
        return profile

    monkeypatch.setattr(github_oauth, "fetch_profile", _fetch)
    return profile


@pytest.fixture
def orcid(monkeypatch):
    """ORCID on, with the profile call faked. Nothing leaves the process."""
    monkeypatch.setattr(orcid_oauth.settings, "orcid_client_id", "APP-CID")
    monkeypatch.setattr(orcid_oauth.settings, "orcid_client_secret", "secret")
    monkeypatch.setattr(orcid_oauth.settings, "orcid_sandbox", True)
    profile = orcid_oauth.OrcidProfile(subject="0000-0002-1825-0097", name="Ada")

    async def _fetch(code):
        return profile

    monkeypatch.setattr(orcid_oauth, "fetch_profile", _fetch)
    return profile


def _providers(db_session, user_id):
    db_session.expire_all()
    return sorted(
        item.provider
        for item in db_session.execute(
            select(Identity).where(Identity.user_id == user_id)
        ).scalars()
    )


@pytest.mark.xfail(strict=True, reason=REASON)
@pytest.mark.parametrize("provider", ["github", "orcid"])
async def test_a_link_finished_after_sign_out_attaches_nothing(
    client, sign_in, db_session, github, orcid, provider
):
    user = sign_in(email="ada@example.edu")
    start = await client.get(f"/auth/{provider}/start", params={"link": True})
    state = parse_qs(urlsplit(start.headers["location"]).query)["state"][0]

    assert (await client.post("/auth/logout")).status_code == 204
    await client.get(
        f"/auth/{provider}/callback", params={"code": "the-code", "state": state}
    )

    assert _providers(db_session, user.id) == ["email"]
