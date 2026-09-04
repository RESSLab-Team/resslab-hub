"""
Unit tests for the HTTP cache middleware (utils/caching.py).

Runs against a stub FastAPI app — no database. The contract under test: data
GETs get a version ETag + Cache-Control, a matching If-None-Match short-circuits
to 304 without invoking the endpoint, repeat GETs for the same URL are served
from the in-process body cache without invoking the endpoint, and bumping the
data version (what a successful upload does) makes the same request serve
fresh content again.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient

from resslab_hub.utils import caching
from resslab_hub.utils.caching import HTTPCacheMiddleware, bump_data_version

MAX_AGE = 123


def make_app() -> tuple[TestClient, dict]:
    app = FastAPI()
    app.add_middleware(HTTPCacheMiddleware, max_age=MAX_AGE)
    calls = {"connections": 0, "contributions": 0}

    @app.get("/connections/")
    def list_connections(query: str = ""):
        calls["connections"] += 1
        return {"items": [1, 2, 3], "query": query}

    @app.get("/connections/csv", response_class=PlainTextResponse)
    def get_csv():
        return "id\n1\n"

    @app.get("/analytics/users")
    def get_users():
        return 42

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.get("/contributions/{number}")
    def get_contribution(number: int):
        calls["contributions"] += 1
        return {"pr_number": number, "head_sha": "abc"}

    # Per-user answers (#247): they must never reach the shared body cache.
    @app.get("/auth/me")
    def me():
        return {"user": None}

    @app.get("/account")
    def account():
        return {"display_name": ""}

    @app.get("/admin/users")
    def admin_users():
        return []

    return TestClient(app), calls


def test_data_get_carries_etag_and_cache_control():
    client, _ = make_app()
    response = client.get("/connections/")
    assert response.status_code == 200
    assert response.headers["cache-control"] == f"public, max-age={MAX_AGE}"
    assert response.headers["etag"] == caching.data_etag()


def test_matching_if_none_match_returns_304_without_running_endpoint():
    client, calls = make_app()
    etag = client.get("/connections/").headers["etag"]
    assert calls["connections"] == 1
    response = client.get("/connections/", headers={"If-None-Match": etag})
    assert response.status_code == 304
    assert response.content == b""
    # Revalidation must refresh the freshness lifetime too.
    assert response.headers["cache-control"] == f"public, max-age={MAX_AGE}"
    assert calls["connections"] == 1  # endpoint not invoked


def test_bumped_data_version_serves_fresh_content():
    client, calls = make_app()
    etag = client.get("/connections/").headers["etag"]
    bump_data_version()
    response = client.get("/connections/", headers={"If-None-Match": etag})
    assert response.status_code == 200
    assert calls["connections"] == 2
    assert response.headers["etag"] != etag


def test_non_json_and_excluded_paths_are_not_cached():
    client, _ = make_app()
    for path in (
        "/connections/csv",
        "/analytics/users",
        "/healthz",
        # Signed-in answers: the cache is keyed on the URL alone and marks what
        # it stores `public`, so caching these would hand one person's account
        # to the next visitor.
        "/auth/me",
        "/account",
        "/admin/users",
    ):
        response = client.get(path)
        assert response.status_code == 200
        assert "cache-control" not in response.headers, path
        assert "etag" not in response.headers, path


def test_contributions_are_never_cached():
    """Submissions live on GitHub and move on their own (#321).

    A cached copy would show a submission that changed or closed since, and
    the editor would build its update on a head commit that no longer exists.
    """
    client, calls = make_app()
    first = client.get("/contributions/7")
    second = client.get("/contributions/7")
    assert calls["contributions"] == 2  # the endpoint ran both times
    assert "cache-control" not in first.headers
    assert "etag" not in second.headers


def test_repeat_get_is_served_from_body_cache_without_running_endpoint():
    client, calls = make_app()
    first = client.get("/connections/")
    second = client.get("/connections/")
    assert calls["connections"] == 1  # endpoint ran only once
    assert second.status_code == 200
    assert second.content == first.content
    assert second.headers["content-type"] == first.headers["content-type"]
    assert second.headers["etag"] == first.headers["etag"]
    assert second.headers["cache-control"] == f"public, max-age={MAX_AGE}"


def test_body_cache_entries_are_keyed_by_full_url():
    client, calls = make_app()
    a = client.get("/connections/", params={"query": "a"})
    b = client.get("/connections/", params={"query": "b"})
    assert calls["connections"] == 2  # distinct query strings, distinct entries
    assert a.json()["query"] == "a"
    assert b.json()["query"] == "b"
    client.get("/connections/", params={"query": "a"})
    client.get("/connections/", params={"query": "b"})
    assert calls["connections"] == 2  # both replays came from the cache


def test_bumped_data_version_invalidates_body_cache():
    client, calls = make_app()
    client.get("/connections/")
    bump_data_version()
    response = client.get("/connections/")  # plain GET, no If-None-Match
    assert response.status_code == 200
    assert calls["connections"] == 2


def test_expired_body_cache_entry_is_recomputed(monkeypatch):
    client, calls = make_app()
    client.get("/connections/")
    now = caching.time.monotonic()
    monkeypatch.setattr(caching.time, "monotonic", lambda: now + MAX_AGE + 1)
    response = client.get("/connections/")
    assert response.status_code == 200
    assert calls["connections"] == 2  # entry outlived max_age, endpoint re-ran


def test_error_responses_are_not_cached():
    app = FastAPI()
    app.add_middleware(HTTPCacheMiddleware, max_age=MAX_AGE)
    calls = {"boom": 0}

    @app.get("/boom/")
    def boom():
        calls["boom"] += 1
        raise HTTPException(status_code=404, detail="nope")

    client = TestClient(app)
    for _ in range(2):
        response = client.get("/boom/")
        assert response.status_code == 404
        assert "etag" not in response.headers
    assert calls["boom"] == 2
