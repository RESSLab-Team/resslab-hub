"""The cross-site write guard (auth/csrf.py)."""

import pytest
from starlette.datastructures import Headers
from starlette.requests import Request

from resslab_hub.auth.csrf import is_same_origin


def _request(method: str = "POST", headers: dict | None = None) -> Request:
    raw = [
        (key.lower().encode(), value.encode())
        for key, value in (headers or {}).items()
    ]
    scope = {
        "type": "http",
        "method": method,
        "path": "/contributions",
        "headers": raw,
        "query_string": b"",
    }
    request = Request(scope)
    assert isinstance(request.headers, Headers)
    return request


@pytest.mark.parametrize("value", ["same-origin", "none"])
def test_our_own_pages_and_typed_urls_pass(value):
    assert is_same_origin(_request(headers={"sec-fetch-site": value}))


@pytest.mark.parametrize("value", ["cross-site", "same-site"])
def test_other_sites_are_refused(value):
    assert not is_same_origin(_request(headers={"sec-fetch-site": value}))


def test_origin_is_the_fallback_when_sec_fetch_site_is_missing():
    assert is_same_origin(
        _request(headers={"origin": "https://resslab-hub.epfl.ch", "host": "resslab-hub.epfl.ch"})
    )
    assert not is_same_origin(
        _request(headers={"origin": "https://evil.example", "host": "resslab-hub.epfl.ch"})
    )


def test_no_browser_headers_at_all_passes():
    # curl with the machine credential sends neither header, and carries no
    # session cookie for a cross-site page to ride on.
    assert is_same_origin(_request(headers={"host": "resslab-hub.epfl.ch"}))
