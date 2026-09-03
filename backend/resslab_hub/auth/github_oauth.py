"""
Sign in with GitHub, and link a GitHub account to an existing user.

This is the user-to-server side of the same GitHub App that opens contribution
pull requests: one App, an installation token for writing to the data repo, and
an OAuth pair here for identifying people. The two credentials are different
and are kept in different settings.

Why it is worth having early: a contributor with a linked GitHub account is
@mentioned on their own pull request, so GitHub notifies them of every review
comment and they can answer where the review happens. Without it a submission
is an anonymous pull request from a bot.

The OAuth ``state`` is a ``LoginChallenge`` row rather than a signed cookie, so
the same table holds every sign-in in progress and the callback works even when
the browser drops cookies on the way back.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from resslab_hub.auth.urls import api_url, safe_redirect
from resslab_hub.config import settings
from resslab_hub.models.database.auth import LoginChallenge

logger = logging.getLogger(__name__)

AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
TOKEN_URL = "https://github.com/login/oauth/access_token"
API_URL = "https://api.github.com"

#: An OAuth round trip is a redirect and back; ten minutes is generous.
STATE_TTL = timedelta(minutes=10)


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
            # Only the address, and only to fill in a new account. Everything
            # the app does to the data repo goes through the installation
            # token, never through the person's own grant.
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
    challenge = LoginChallenge(
        kind="oauth_github",
        redirect_to=safe_redirect(redirect_to),
        link_user_id=link_user_id,
        ip=ip,
        expires_at=datetime.now(timezone.utc) + STATE_TTL,
    )
    db.add(challenge)
    await db.flush()
    await db.commit()
    return challenge.id


async def consume_state(
    db: AsyncSession, state: str
) -> Optional[LoginChallenge]:
    """Look up and burn a ``state``. None when unknown, used or expired."""
    if not state:
        return None
    result = await db.execute(
        select(LoginChallenge).where(
            LoginChallenge.id == state, LoginChallenge.kind == "oauth_github"
        )
    )
    challenge = result.scalar_one_or_none()
    if challenge is None or challenge.consumed_at is not None:
        return None
    expires_at = challenge.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        return None
    challenge.consumed_at = datetime.now(timezone.utc)
    await db.commit()
    return challenge


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
            # Only the primary verified address, and only to fill in a new
            # account. An unverified one proves nothing.
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
