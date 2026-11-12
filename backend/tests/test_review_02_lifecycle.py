# ruff: noqa: F811 (the fixtures are imported from the other test files)
"""
Review 02, questions 5 and 6: disable an account, remove an identity.

Each test asserts the behaviour we want and is marked xfail(strict): it fails
today and starts to pass when the finding is fixed. See
docs/review/findings/02-identity.md.
"""

import asyncio
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import select

from resslab_hub.models.database.auth import Identity, User
from tests.test_admin import _identity, _no_config_grants  # noqa: F401
from tests.test_auth_flow import (  # noqa: F401
    ORCID_ID,
    _no_rate_limits,
    github,
)


def _identities(db_session, user_id):
    db_session.expire_all()
    return (
        db_session.execute(select(Identity).where(Identity.user_id == user_id))
        .scalars()
        .all()
    )


@pytest.mark.xfail(strict=True, reason="review 02: 02-7")
async def test_a_link_does_not_land_on_an_account_disabled_meanwhile(
    client, github, sign_in, db_session
):
    """The person starts a GitHub link, an admin disables the account, then
    GitHub sends the browser back. The link callback trusts ``link_user_id``
    and never looks at ``disabled_at``: today GitHub is linked anyway."""
    user = sign_in(email="ada@example.edu")
    response = await client.get(
        "/auth/github/start", params={"link": True, "redirect_to": "/account"}
    )
    state = parse_qs(urlsplit(response.headers["location"]).query)["state"][0]
    user.disabled_at = datetime.now(timezone.utc)
    db_session.commit()

    callback = await client.get(
        "/auth/github/callback", params={"code": "the-code", "state": state}
    )

    assert "error=" in callback.headers["location"]
    providers = [item.provider for item in _identities(db_session, user.id)]
    assert "github" not in providers


@pytest.mark.xfail(strict=True, reason="review 02: 02-8")
async def test_the_main_address_always_has_its_identity(client, sign_in, db_session):
    """Two tabs: one makes an added address the main one, the other removes
    it. Each request checks against the state it read, so both pass: today
    ``User.email`` names an address that is no longer an identity."""
    user = sign_in(email="ada@example.edu", emails=("ada@epfl.ch",))
    added = next(
        item.id
        for item in _identities(db_session, user.id)
        if item.subject == "ada@epfl.ch"
    )

    await asyncio.gather(
        client.post(f"/auth/identities/{added}/main"),
        client.delete(f"/auth/identities/{added}"),
    )

    stored = db_session.get(User, user.id)
    subjects = {item.subject for item in _identities(db_session, user.id)}
    assert stored.email in subjects


@pytest.mark.xfail(strict=True, reason="review 02: 02-9")
async def test_two_unlinks_at_once_keep_one_way_in(client, sign_in, db_session):
    """An account with no address, a GitHub login and an ORCID iD. Two tabs
    unlink one each. ``remove_identity`` counts the identities in Python, so
    both see two: today the account has no way in left."""
    user = sign_in(email=None, provider="github", verified=False, github_login="ada")
    _identity(db_session, user, "orcid", ORCID_ID)
    ids = [item.id for item in _identities(db_session, user.id)]
    assert len(ids) == 2

    await asyncio.gather(*(client.delete(f"/auth/identities/{i}") for i in ids))

    assert len(_identities(db_session, user.id)) >= 1
