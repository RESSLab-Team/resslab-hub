"""
Unit tests for the HTTP cache middleware (utils/caching.py).

Runs against a stub FastAPI app — no database. The contract under test: data
GETs get a version ETag + Cache-Control, a matching If-None-Match short-circuits
to 304 without invoking the endpoint, and bumping the data version (what a
successful upload does) makes the same request serve fresh content again.
"""

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient

from resslab_hub.utils import caching
from resslab_hub.utils.caching import HTTPCacheMiddleware, bump_data_version

MAX_AGE = 123


def make_app() -> tuple[TestClient, dict]:
    app = FastAPI()
    app.add_middleware(HTTPCacheMiddleware, max_age=MAX_AGE)
    calls = {"connections": 0}

    @app.get("/connections/")
    def list_connections():
        calls["connections"] += 1
        return {"items": [1, 2, 3]}

    @app.get("/connections/csv", response_class=PlainTextResponse)
    def get_csv():
        return "id\n1\n"

    @app.get("/analytics/users")
    def get_users():
        return 42

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

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
    for path in ("/connections/csv", "/analytics/users", "/healthz"):
        response = client.get(path)
        assert response.status_code == 200
        assert "cache-control" not in response.headers, path
        assert "etag" not in response.headers, path
