"""
Sign in with GitHub, and link a GitHub account to an existing user.

This is the user-to-server side of a GitHub App: an OAuth pair for identifying
people, separate from the installation token that writes to the data repo. In
the deployments it is the App that opens the pull requests; locally a dev App
with a loopback callback (docs/src/auth.md).

The OAuth ``state`` is a ``LoginChallenge`` row whose id also goes in the
``resslab_login`` cookie, so the callback only works in the browser that
started the round trip (``oauth_state``, shared with ORCID).
"""

from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlencode

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from resslab_hub.auth import oauth_state
from resslab_hub.auth.urls import api_url
from resslab_hub.config import settings
from resslab_hub.models.database.auth import LoginChallenge

AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
TOKEN_URL = "https://github.com/login/oauth/access_token"
API_URL = "https://api.github.com"

#: The ``LoginChallenge.kind`` of a GitHub round trip.
KIND = "oauth_github"


class GitHubOAuthError(Exception):
    """GitHub refused the exchange, or answered something unusable."""


@dataclass
class GitHubProfile:
    #: The numeric account id: immutable, unlike the login.
    subject: str
    login: str
    name: str = ""
    email: Optional[str] = None
    email_verified: bool = False


def configured() -> bool:
    """True when the App's OAuth pair is set up."""
    return bool(settings.github_oauth_client_id and settings.github_oauth_client_secret)


def callback_url() -> str:
    return api_url("/auth/github/callback")


def authorize_url(state: str) -> str:
    query = urlencode(
        {
            "client_id": str(settings.github_oauth_client_id),
            "redirect_uri": callback_url(),
            # Only who they are and their address. Writing to the data repo
            # goes through the installation token, never a person's grant.
            "scope": "read:user user:email",
            "state": state,
        }
    )
    return f"{AUTHORIZE_URL}?{query}"


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
    """Look up and burn a GitHub ``state`` (see ``oauth_state``)."""
    return await oauth_state.consume_state(db, KIND, state, expected)


async def exchange_code(code: str) -> str:
    """Trade the callback code for a user access token."""
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": str(settings.github_oauth_client_id),
                "client_secret": str(settings.github_oauth_client_secret),
                "code": code,
                "redirect_uri": callback_url(),
            },
        )
    if response.status_code != 200:
        raise GitHubOAuthError(f"token endpoint answered {response.status_code}")
    payload = response.json()
    token = payload.get("access_token")
    if not token:
        raise GitHubOAuthError(str(payload.get("error", "no access_token")))
    return token


async def fetch_user(token: str) -> GitHubProfile:
    """Read the account behind a user token, with a verified address if any."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    async with httpx.AsyncClient(timeout=10, headers=headers) as client:
        response = await client.get(f"{API_URL}/user")
        if response.status_code != 200:
            raise GitHubOAuthError(f"/user answered {response.status_code}")
        account = response.json()
        email, verified = account.get("email"), False
        mails = await client.get(f"{API_URL}/user/emails")
        if mails.status_code == 200:
            # Only the primary verified address. An unverified one proves
            # nothing.
            for entry in mails.json():
                if entry.get("primary") and entry.get("verified"):
                    email, verified = entry.get("email"), True
                    break
    return GitHubProfile(
        subject=str(account["id"]),
        login=account.get("login", ""),
        name=account.get("name") or "",
        email=email,
        email_verified=verified,
    )


async def fetch_profile(code: str) -> GitHubProfile:
    """The whole callback side: code in, profile out."""
    return await fetch_user(await exchange_code(code))
