"""
Review 03 (roles): how a stored role follows its sources.

Each test states what should happen and fails today, so it is marked
``xfail(strict=True)``. See ``docs/review/findings/03-roles.md``.
"""

from datetime import datetime, timedelta, timezone

import pytest

from resslab_hub.auth import roles


@pytest.fixture(autouse=True)
def _no_config_grants(monkeypatch):
    monkeypatch.setattr(roles.settings, "admin_emails", "")
    monkeypatch.setattr(roles.settings, "contributor_domains", "")


@pytest.mark.xfail(strict=True, reason="review 03: 03-1")
async def test_an_address_removed_from_admin_emails_is_no_longer_admin(client, sign_in):
    # Signed in while the address was in ADMIN_EMAILS. Then the address
    # leaves ADMIN_EMAILS (the fixture above empties it) and the backend
    # restarts. The session is still valid for up to 30 days.
    sign_in(email="boss@epfl.ch", role="admin", role_source="admin-email")

    response = await client.get("/admin/users")

    # Today: 200, the stored role is never worked out again for an account
    # with no GitHub login, until the next sign-in.
    assert response.status_code == 403


@pytest.mark.xfail(strict=True, reason="review 03: 03-3")
async def test_a_github_role_is_not_read_from_a_login_someone_else_took(
    client, sign_in, github_permissions
):
    # Ada linked GitHub as "old-name" (GitHub id 90000 in the fixture) and had
    # write access. She renamed her GitHub login. Someone else took
    # "old-name", and that person is admin on the data repo.
    long_ago = datetime.now(timezone.utc) - timedelta(days=2)
    sign_in(
        email="ada@example.com",
        provider="github",
        role="curator",
        role_source="github",
        github_login="old-name",
        github_role="write",
        github_role_synced_at=long_ago,
    )
    github_permissions["old-name"] = "admin"

    user = (await client.get("/auth/me")).json()["user"]

    # Today: "admin". The sync asks GitHub by login name, not by the id of
    # the linked identity, so Ada gets the permission of the new holder.
    assert user["role"] != "admin"
