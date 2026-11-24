# ruff: noqa: F811 (the fixtures are imported from the other test files)
"""
Review 02, questions 3 and 4: the bare join and the admin merge.

Each test asserts the behaviour we want and is marked xfail(strict): it fails
today and starts to pass when the finding is fixed. See
docs/archive/review/findings/02-identity.md.
"""

import pytest

from resslab_hub.auth import roles
from resslab_hub.models.database.auth import User
from tests.test_admin import _identity, _no_config_grants, _user  # noqa: F401
from tests.test_auth_flow import (  # noqa: F401
    ORCID_ID,
    _add,
    _no_rate_limits,
    _orcid,
    _orcid_owner,
    mailbox,
    orcid,
)


@pytest.mark.xfail(strict=True, reason="review 02: 02-3")
async def test_a_bare_join_keeps_the_role_an_admin_gave(
    client, orcid, mailbox, db_session
):
    """An admin made the ORCID-only account a curator. Then the person adds
    the address of their main account, and the two join.

    ``absorb_bare_account`` copies the name, the iD and the GitHub mirror,
    not ``role_override``: today the curator role is gone.
    """
    holder = _user(db_session, "ada@epfl.ch")
    _identity(db_session, holder, "email", "ada@epfl.ch")
    holder_id = holder.id
    await _orcid(client)
    bare = db_session.get(User, _orcid_owner(db_session))
    bare.role_override = "curator"
    db_session.commit()

    response = await _add(client, mailbox, "ada@epfl.ch")

    assert response.status_code == 200
    assert response.json()["id"] == holder_id
    assert response.json()["role"] == "curator"


def _with_orcid(db_session, email, orcid_id):
    user = _user(db_session, email)
    _identity(db_session, user, "email", email)
    _identity(db_session, user, "orcid", orcid_id)
    user.orcid = orcid_id
    db_session.commit()
    return user


@pytest.mark.xfail(strict=True, reason="review 02: 02-4")
async def test_a_merge_of_two_orcid_accounts_is_refused(client, sign_in, db_session):
    """Two GitHub logins are refused (``both_github``). Two ORCID iDs are not:
    today ``keep`` ends with two iDs and one ``orcid`` field."""
    keep = _with_orcid(db_session, "ada@epfl.ch", "0000-0001-5109-3700")
    other = _with_orcid(db_session, "ada@gmail.com", ORCID_ID)
    keep_id, other_id = keep.id, other.id
    sign_in(email="me@example.org", role="admin", role_override="admin")

    response = await client.post(
        f"/admin/users/{keep_id}/merge", json={"from_user_id": other_id}
    )

    assert response.status_code == 409
    db_session.expire_all()
    assert db_session.get(User, other_id) is not None


@pytest.mark.xfail(strict=True, reason="review 02: 02-5")
async def test_a_merge_cannot_fold_a_locked_admin_away(
    client, sign_in, db_session, monkeypatch
):
    """``PATCH /admin/users/{id}`` refuses to touch a config admin
    (``locked_admin``). The merge does not check it: today the config admin's
    account is deleted and its address moves to another person's account."""
    monkeypatch.setattr(roles.settings, "admin_emails", "boss@epfl.ch")
    boss = _user(db_session, "boss@epfl.ch", role="admin", role_source="admin-email")
    _identity(db_session, boss, "email", "boss@epfl.ch")
    keep = _user(db_session, "eve@example.org")
    _identity(db_session, keep, "email", "eve@example.org")
    boss_id, keep_id = boss.id, keep.id
    sign_in(email="me@example.org", role="admin", role_override="admin")

    response = await client.post(
        f"/admin/users/{keep_id}/merge", json={"from_user_id": boss_id}
    )

    assert response.status_code in (403, 409)
    db_session.expire_all()
    assert db_session.get(User, boss_id) is not None
