"""The ORCID client alone: what it sends to ORCID and what it makes of the answer.

ORCID is faked with an httpx MockTransport, so nothing leaves the process.
The sign-in flow around it is in test_auth_flow.py.
"""

from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from resslab_hub.auth import orcid_oauth

IDENTIFIER = "0000-0002-1825-0097"


@pytest.fixture
def keys(monkeypatch):
    monkeypatch.setattr(orcid_oauth.settings, "orcid_client_id", "APP-CID")
    monkeypatch.setattr(orcid_oauth.settings, "orcid_client_secret", "the-secret")
    monkeypatch.setattr(orcid_oauth.settings, "orcid_sandbox", True)


def fake_orcid(monkeypatch, status=200, body=None, seen=None):
    """Answer the token call with ``body``; keep the request in ``seen``."""

    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        if isinstance(body, (dict, list)):
            return httpx.Response(status, json=body)
        return httpx.Response(status, text=body or "")

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        orcid_oauth, "_client", lambda: httpx.AsyncClient(transport=transport)
    )


def token_answer(**extra):
    answer = {
        "access_token": "token",
        "token_type": "bearer",
        "refresh_token": "refresh",
        "expires_in": 631138518,
        "scope": "/authenticate",
        "name": "Ada Lovelace",
        "orcid": IDENTIFIER,
    }
    answer.update(extra)
    return answer


def test_configured_needs_both_keys(monkeypatch):
    monkeypatch.setattr(orcid_oauth.settings, "orcid_client_id", "APP-CID")
    monkeypatch.setattr(orcid_oauth.settings, "orcid_client_secret", None)
    assert not orcid_oauth.configured()
    monkeypatch.setattr(orcid_oauth.settings, "orcid_client_secret", "s")
    assert orcid_oauth.configured()


@pytest.mark.parametrize(
    "value, expected",
    [
        (True, "https://sandbox.orcid.org"),
        ("true", "https://sandbox.orcid.org"),
        (False, "https://orcid.org"),
        ("false", "https://orcid.org"),
        (None, "https://orcid.org"),
    ],
)
def test_sandbox_flag_picks_the_host(monkeypatch, value, expected):
    monkeypatch.setattr(orcid_oauth.settings, "orcid_sandbox", value)
    assert orcid_oauth.host() == expected


def test_authorize_url(keys):
    url = urlsplit(orcid_oauth.authorize_url("the-state"))
    assert f"{url.scheme}://{url.netloc}{url.path}" == (
        "https://sandbox.orcid.org/oauth/authorize"
    )
    query = parse_qs(url.query)
    assert query["client_id"] == ["APP-CID"]
    assert query["response_type"] == ["code"]
    assert query["scope"] == ["/authenticate"]
    assert query["state"] == ["the-state"]
    assert query["redirect_uri"] == [orcid_oauth.callback_url()]
    assert query["redirect_uri"][0].endswith("/auth/orcid/callback")


async def test_profile_from_the_token_answer(keys, monkeypatch):
    seen = []
    fake_orcid(monkeypatch, body=token_answer(), seen=seen)
    profile = await orcid_oauth.fetch_profile("the-code")
    assert profile == orcid_oauth.OrcidProfile(subject=IDENTIFIER, name="Ada Lovelace")

    # One call only, to the token endpoint, with what ORCID asks for.
    assert len(seen) == 1
    request = seen[0]
    assert request.method == "POST"
    assert str(request.url) == "https://sandbox.orcid.org/oauth/token"
    assert request.headers["accept"] == "application/json"
    form = parse_qs(request.content.decode())
    assert form == {
        "client_id": ["APP-CID"],
        "client_secret": ["the-secret"],
        "grant_type": ["authorization_code"],
        "code": ["the-code"],
        "redirect_uri": [orcid_oauth.callback_url()],
    }


async def test_private_name_gives_an_empty_name(keys, monkeypatch):
    fake_orcid(monkeypatch, body=token_answer(name=None))
    profile = await orcid_oauth.fetch_profile("the-code")
    assert profile.name == ""


async def test_checksum_x_is_a_valid_id(keys, monkeypatch):
    fake_orcid(monkeypatch, body=token_answer(orcid="0000-0002-9079-593X"))
    profile = await orcid_oauth.fetch_profile("the-code")
    assert profile.subject == "0000-0002-9079-593X"


@pytest.mark.parametrize(
    "status, body",
    [
        (400, {"error": "invalid_grant", "error_description": "Reused code"}),
        (401, {"error": "invalid_client"}),
        (200, {"error": "server_error"}),
        (500, "<html>down</html>"),
        (200, "not json"),
        (200, ["a", "list"]),
        (200, token_answer(orcid=None)),
        (200, token_answer(orcid="")),
        (200, token_answer(orcid="0000-0002-1825-009")),
        (200, token_answer(orcid="../../etc/passwd")),
        (200, token_answer(orcid="https://orcid.org/0000-0002-1825-0097")),
    ],
)
async def test_unusable_answers_raise(keys, monkeypatch, status, body):
    fake_orcid(monkeypatch, status=status, body=body)
    with pytest.raises(orcid_oauth.OrcidOAuthError):
        await orcid_oauth.fetch_profile("the-code")


async def test_network_error_raises(keys, monkeypatch):
    def handler(request):
        raise httpx.ConnectError("no route", request=request)

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        orcid_oauth, "_client", lambda: httpx.AsyncClient(transport=transport)
    )
    with pytest.raises(orcid_oauth.OrcidOAuthError):
        await orcid_oauth.fetch_profile("the-code")
