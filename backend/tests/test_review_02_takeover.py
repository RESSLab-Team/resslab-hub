# ruff: noqa: F811 (the fixtures are imported from the other test files)
"""
Review 02, questions 1 and 2: who can get into an account.

Each test asserts the behaviour we want and is marked xfail(strict): it fails
today and starts to pass when the finding is fixed. See
docs/review/findings/02-identity.md.
"""

import asyncio
from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import select

from resslab_hub.models.database.auth import Identity, User
from tests.test_admin import _identity, _no_config_grants  # noqa: F401
from tests.test_auth_flow import (  # noqa: F401
    ORCID_ID,
    _no_rate_limits,
    _orcid,
    github,
    mailbox,
    orcid,
)


def _link_parts(link):
    query = parse_qs(urlsplit(link).query)
    return {"challenge": query["challenge"][0], "token": query["token"][0]}


@pytest.mark.xfail(strict=True, reason="review 02: 02-1")
async def test_two_first_sign_ins_at_once_make_no_500(client, mailbox, db_session):
    """Two tabs finish the first sign-in of a new address at the same time.

    Today the second one hits auth_user_email_key and answers 500.
    """
    for _ in range(2):
        await client.post("/auth/email/start", json={"email": "new@example.org"})
    first, second = (_link_parts(mail["link"]) for mail in mailbox[-2:])

    responses = await asyncio.gather(
        client.post("/auth/email/verify", json=first),
        client.post("/auth/email/verify", json=second),
        return_exceptions=True,
    )

    assert all(not isinstance(item, Exception) for item in responses), responses
    assert sorted(item.status_code for item in responses) == [200, 200]
    users = db_session.execute(select(User)).scalars().all()
    assert len(users) == 1


async def _github_link(client):
    response = await client.get(
        "/auth/github/start", params={"link": True, "redirect_to": "/account"}
    )
    state = parse_qs(urlsplit(response.headers["location"]).query)["state"][0]
    return await client.get(
        "/auth/github/callback", params={"code": "the-code", "state": state}
    )


@pytest.mark.xfail(strict=True, reason="review 02: 02-2")
async def test_an_account_cannot_link_a_second_github(
    client, github, sign_in, db_session
):
    """``attach_identity`` has no "one GitHub per account" rule.

    Today the second GitHub is added, ``github_login`` now names it, and
    removing it later clears the mirror while the first one stays linked.
    """
    user = sign_in(email="ada@example.edu", github_login="old-ada")
    _identity(db_session, user, "github", "1111")

    response = await _github_link(client)

    assert "error=" in response.headers["location"]
    db_session.expire_all()
    subjects = db_session.execute(
        select(Identity.subject).where(
            Identity.user_id == user.id, Identity.provider == "github"
        )
    ).scalars()
    assert sorted(subjects) == ["1111"]
    assert db_session.get(User, user.id).github_login == "old-ada"


@pytest.mark.xfail(strict=True, reason="review 02: 02-2")
async def test_an_account_cannot_link_a_second_orcid(
    client, orcid, sign_in, db_session
):
    """Same for ORCID: today the account ends with two iDs, and ``orcid``
    names only the last one."""
    user = sign_in(email="ada@example.edu", orcid="0000-0001-5109-3700")
    _identity(db_session, user, "orcid", "0000-0001-5109-3700")

    response = await _orcid(client, redirect_to="/account", link=True)

    assert "error=" in response.headers["location"]
    db_session.expire_all()
    subjects = db_session.execute(
        select(Identity.subject).where(
            Identity.user_id == user.id, Identity.provider == "orcid"
        )
    ).scalars()
    assert sorted(subjects) == ["0000-0001-5109-3700"]
    assert db_session.get(User, user.id).orcid != ORCID_ID
