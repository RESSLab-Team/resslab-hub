"""
The CONTRIBUTIONS_ENABLED switch: `GET /features` and the 404 gate.

Over HTTP, because the gate is a FastAPI dependency. No Postgres needed: the
gate answers before any sign-in check, `/auth/me` without a cookie never
queries, and an anonymous caller is refused before the database either way.
So this file builds its own client instead of using the `client` fixture,
which empties the tables first.
"""

import httpx
import pytest
import pytest_asyncio

from resslab_hub.config import settings


@pytest_asyncio.fixture
async def http():
    from resslab_hub.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def app_configured(monkeypatch):
    monkeypatch.setattr(settings, "github_app_id", "1")
    monkeypatch.setattr(settings, "github_app_private_key", "key")
    monkeypatch.setattr(settings, "github_app_installation_id", "2")


@pytest.fixture
def app_missing(monkeypatch):
    monkeypatch.setattr(settings, "github_app_id", None)
    monkeypatch.setattr(settings, "github_app_private_key", None)
    monkeypatch.setattr(settings, "github_app_installation_id", None)


@pytest.fixture
def switched_off(monkeypatch):
    monkeypatch.setattr(settings, "contributions_enabled", False)


@pytest.fixture
def switched_on(monkeypatch):
    monkeypatch.setattr(settings, "contributions_enabled", True)


# --- GET /features ----------------------------------------------------------
async def test_features_on_with_a_github_app(http, switched_on, app_configured):
    response = await http.get("/features")
    assert response.status_code == 200
    assert response.json() == {"contributions": True}
    # Never kept by a browser or the response cache: it changes on a restart.
    assert response.headers["cache-control"] == "no-store"
    assert "etag" not in response.headers


async def test_features_off_when_switched_off(http, switched_off, app_configured):
    response = await http.get("/features")
    assert response.json() == {"contributions": False}


async def test_features_off_without_a_github_app(http, switched_on, app_missing):
    # Nothing could be submitted, so the interface has nothing to show.
    response = await http.get("/features")
    assert response.json() == {"contributions": False}


# --- the gate ---------------------------------------------------------------
@pytest.mark.parametrize(
    "method, path",
    [
        ("POST", "/contributions"),
        ("PUT", "/contributions/7"),
        ("GET", "/contributions"),
        ("GET", "/contributions/7"),
        ("GET", "/contributions/7/validation"),
        ("GET", "/contributions/7/comments"),
        ("GET", "/contributions/7/files?path=x.csv"),
        ("POST", "/auth/email/start"),
        ("POST", "/auth/email/verify"),
        ("POST", "/auth/logout"),
        ("GET", "/auth/identities"),
        ("DELETE", "/auth/identities/abc"),
        ("GET", "/auth/github/start"),
        ("GET", "/auth/github/callback"),
    ],
)
async def test_pipeline_answers_404_when_switched_off(
    http, switched_off, app_configured, method, path
):
    response = await http.request(method, path)
    assert response.status_code == 404, (method, path)
    assert response.json() == {
        "detail": "Contributions are not enabled on this deployment."
    }


async def test_me_stays_anonymous_when_switched_off(http, switched_off):
    # The sidebar asks it on every page: it must keep saying "nobody".
    response = await http.get("/auth/me")
    assert response.status_code == 200
    assert response.json() == {"user": None}


async def test_gate_is_transparent_when_switched_on(http, switched_on, app_configured):
    # The usual sign-in check answers, not the gate.
    assert (await http.get("/auth/identities")).status_code == 401
    assert (await http.get("/contributions")).status_code == 401
    assert (await http.post("/contributions")).status_code == 401
