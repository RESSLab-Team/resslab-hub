"""
Sign in with ORCID, and link an ORCID iD to an existing user (#250).

A client of the ORCID public API, made in Developer Tools on orcid.org (or
sandbox.orcid.org for tests). It is free and self-service, EPFL has nothing
to register.

We only ask for ``/authenticate``: who the person is. The token answer
already holds the iD and the name, so one call is enough. We never read the
address from ORCID: it is rarely public, and the address of an account is
always proved with our own mailed code (docs/src/auth.md). The access token is
thrown away.

The ``state`` works like GitHub's (``oauth_state``), with its own kind.
"""

import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlencode

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from resslab_hub.auth import oauth_state
from resslab_hub.auth.urls import api_url
from resslab_hub.config import settings
from resslab_hub.models.database.auth import LoginChallenge

#: The ``LoginChallenge.kind`` of an ORCID round trip.
KIND = "oauth_orcid"

#: Four groups of four digits, the last character may be X (a checksum).
ORCID_ID = re.compile(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]")


class OrcidOAuthError(Exception):
    """ORCID refused the exchange, or answered something unusable."""


@dataclass
class OrcidProfile:
    #: The ORCID iD, like 0000-0002-1825-0097. It never changes.
    subject: str
    #: The name on the record, empty when the person keeps it private.
    name: str = ""


def configured() -> bool:
    """True when the client id and secret are set."""
    return bool(settings.orcid_client_id and settings.orcid_client_secret)


def _sandbox() -> bool:
    value = settings.orcid_sandbox
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


def host() -> str:
    return "https://sandbox.orcid.org" if _sandbox() else "https://orcid.org"


def callback_url() -> str:
    return api_url("/auth/orcid/callback")


def authorize_url(state: str) -> str:
    query = urlencode(
        {
            "client_id": str(settings.orcid_client_id),
            "response_type": "code",
            "scope": "/authenticate",
            "redirect_uri": callback_url(),
            "state": state,
        }
    )
    return f"{host()}/oauth/authorize?{query}"


async def start(
    db: AsyncSession,
    redirect_to: str = "/",
    link_user_id: Optional[str] = None,
    ip: str = "",
) -> str:
    """Record a pending round trip; its row id is the OAuth ``state``."""
    return await oauth_state.start(db, KIND, redirect_to, link_user_id, ip)


async def consume_state(
    db: AsyncSession, state: str, expected: str
) -> Optional[LoginChallenge]:
    """Look up and burn an ORCID ``state`` (see ``oauth_state``)."""
    return await oauth_state.consume_state(db, KIND, state, expected)


def _client() -> httpx.AsyncClient:
    """Every call to ORCID goes through here, so the tests can swap it."""
    return httpx.AsyncClient(timeout=10)


async def fetch_profile(code: str) -> OrcidProfile:
    """The whole callback side: trade the code, read the iD and the name.

    The iD comes back on this server-to-server call, which our client secret
    authenticates. So it is proved, no ``id_token`` to check.
    """
    try:
        async with _client() as client:
            response = await client.post(
                f"{host()}/oauth/token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": str(settings.orcid_client_id),
                    "client_secret": str(settings.orcid_client_secret),
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": callback_url(),
                },
            )
    except httpx.HTTPError as exc:
        raise OrcidOAuthError(f"token endpoint unreachable: {exc}") from exc
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    if response.status_code != 200 or payload.get("error"):
        raise OrcidOAuthError(
            f"token endpoint answered {response.status_code}: "
            f"{payload.get('error', 'no error field')}"
        )
    orcid = str(payload.get("orcid") or "")
    # It goes in URLs and in commit trailers: only a well-formed iD.
    if not ORCID_ID.fullmatch(orcid):
        raise OrcidOAuthError("no valid ORCID iD in the token answer")
    return OrcidProfile(subject=orcid, name=str(payload.get("name") or "").strip())
