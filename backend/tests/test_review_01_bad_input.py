"""
Review 01, finding 01-1: bad input on the sign-in routes gives a 500.

The challenge id and the OAuth state go straight to a SELECT on a Postgres
UUID column, and ``redirect_to`` goes into a ``String(500)`` column. Nothing
checks them before. Each test asks for an answer below 500, so each one fails
today. See docs/review/findings/01-sign-in.md.
"""

import httpx
import pytest

from resslab_hub.auth import mailer
from resslab_hub.utils.rate_limit import limiter

REASON = "review 01: 01-1"


@pytest.fixture(autouse=True)
def _no_rate_limits(monkeypatch):
    monkeypatch.setattr(limiter, "enabled", False)


@pytest.fixture(autouse=True)
def _no_mail(monkeypatch):
    async def _send(*args):
        return None

    monkeypatch.setattr(mailer, "send_login_mail", _send)


@pytest.fixture
async def raw_client(_clean_tables):
    """Like ``client``, but a server error comes back as a 500 response."""
    from resslab_hub.main import app
    from resslab_hub.utils.database import engine

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await engine.dispose()


@pytest.mark.xfail(strict=True, reason=REASON)
async def test_a_challenge_that_is_not_a_uuid(raw_client):
    response = await raw_client.post(
        "/auth/email/verify", json={"challenge": "not-a-uuid", "token": "x"}
    )
    assert response.status_code < 500


@pytest.mark.xfail(strict=True, reason=REASON)
async def test_a_login_cookie_that_is_not_a_uuid(raw_client):
    raw_client.cookies.set("resslab_login", "abc")
    response = await raw_client.post("/auth/email/verify", json={"code": "123456"})
    assert response.status_code < 500


@pytest.mark.xfail(strict=True, reason=REASON)
async def test_a_nul_in_the_challenge(raw_client):
    response = await raw_client.post(
        "/auth/email/verify", json={"challenge": "a\x00b", "token": "x"}
    )
    assert response.status_code < 500


@pytest.mark.xfail(strict=True, reason=REASON)
async def test_a_redirect_longer_than_the_column(raw_client):
    response = await raw_client.post(
        "/auth/email/start",
        json={"email": "ada@example.edu", "redirect_to": "/" + "a" * 600},
    )
    assert response.status_code < 500


@pytest.mark.xfail(strict=True, reason=REASON)
async def test_a_nul_in_the_redirect(raw_client):
    response = await raw_client.post(
        "/auth/email/start",
        json={"email": "ada@example.edu", "redirect_to": "/a\x00b"},
    )
    assert response.status_code < 500


@pytest.mark.xfail(strict=True, reason=REASON)
@pytest.mark.parametrize("provider", ["github", "orcid"])
async def test_a_state_that_is_not_a_uuid(raw_client, provider):
    # state == cookie, so consume_state goes on to the SELECT. Nothing is sent
    # to GitHub or ORCID: it fails before.
    raw_client.cookies.set("resslab_login", "abc")
    response = await raw_client.get(
        f"/auth/{provider}/callback", params={"state": "abc", "code": "x"}
    )
    assert response.status_code < 500


# --- 01-1 also: a long profile name at the first sign-in -----------------
# ``display_name`` is String(200) and the callbacks copy the provider's name
# into it without cutting it (routers/auth.py:559 and :678).


@pytest.fixture
def long_github_name(monkeypatch):
    from resslab_hub.auth import github_oauth

    monkeypatch.setattr(github_oauth.settings, "github_oauth_client_id", "cid")
    monkeypatch.setattr(github_oauth.settings, "github_oauth_client_secret", "secret")
    profile = github_oauth.GitHubProfile(
        subject="4242",
        login="ada",
        name="A" * 255,
        email="ada@example.edu",
        email_verified=True,
    )

    async def _fetch(code):
        return profile

    monkeypatch.setattr(github_oauth, "fetch_profile", _fetch)


@pytest.mark.xfail(strict=True, reason=REASON)
async def test_a_long_github_name_at_first_sign_in(raw_client, long_github_name):
    start = await raw_client.get("/auth/github/start", params={"redirect_to": "/"})
    state = start.headers["location"].split("state=")[1].split("&")[0]
    response = await raw_client.get(
        "/auth/github/callback", params={"code": "the-code", "state": state}
    )
    assert response.status_code < 500
