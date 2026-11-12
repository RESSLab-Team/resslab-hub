"""
Review 03 (roles): the admin page and the accounts it may not touch.

Each test states what should happen and fails today, so it is marked
``xfail(strict=True)``. See ``docs/review/findings/03-roles.md``.
"""

from datetime import datetime, timezone

import pytest

from resslab_hub.auth import roles
from resslab_hub.models.database.auth import Identity, User


@pytest.fixture(autouse=True)
def _one_configured_admin(monkeypatch):
    monkeypatch.setattr(roles.settings, "admin_emails", "boss@epfl.ch")
    monkeypatch.setattr(roles.settings, "contributor_domains", "")


def _account(db_session, email, **fields):
    user = User(
        email=email,
        email_verified_at=datetime.now(timezone.utc),
        display_name=email.split("@")[0].title(),
        **fields,
    )
    db_session.add(user)
    db_session.flush()
    db_session.add(
        Identity(user_id=user.id, provider="email", subject=email, handle=email)
    )
    db_session.commit()
    return user


@pytest.mark.xfail(strict=True, reason="review 03: 03-2")
async def test_an_admin_cannot_merge_a_locked_admin_away(client, sign_in, db_session):
    boss = _account(db_session, "boss@epfl.ch", role="admin", role_source="admin-email")
    other = _account(db_session, "someone@example.com", role="viewer")
    boss_id, other_id = boss.id, other.id
    sign_in(email="me@example.org", role="admin", role_override="admin")

    # The same admin cannot change this account with PATCH.
    patch = await client.patch(f"/admin/users/{boss_id}", json={"disabled": True})
    assert patch.json()["detail"] == "locked_admin"

    response = await client.post(
        f"/admin/users/{other_id}/merge", json={"from_user_id": boss_id}
    )

    # Today: 200. The locked admin's account is deleted, its sessions end,
    # and its address now signs in to the other account.
    assert response.status_code == 403
    assert response.json()["detail"] == "locked_admin"
