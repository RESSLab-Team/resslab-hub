"""
The admin endpoints and the access requests, over HTTP (#248).

Like ``test_auth_flow.py``: the role gates are FastAPI dependencies, so
everything goes through the ``client`` fixture.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from resslab_hub.auth import email_login, mailer, roles
from resslab_hub.auth.tokens import hash_token, new_token
from resslab_hub.models.database.auth import (
    AccessRequest,
    Identity,
    Invitation,
    Session,
    User,
)
from resslab_hub.utils.rate_limit import limiter


@pytest.fixture(autouse=True)
def _no_rate_limits(monkeypatch):
    monkeypatch.setattr(limiter, "enabled", False)


@pytest.fixture(autouse=True)
def _no_config_grants(monkeypatch):
    """Whatever ``secrets/.env`` says, start with no configured admin."""
    monkeypatch.setattr(roles.settings, "admin_emails", "")
    monkeypatch.setattr(roles.settings, "contributor_domains", "")


@pytest.fixture
def outbox(monkeypatch):
    """The notices that would have been mailed."""
    sent = []

    async def _send(email, subject, title, paragraphs, button, link, footnote):
        sent.append({"to": email, "subject": subject, "body": paragraphs, "link": link})

    monkeypatch.setattr(mailer, "send_notice", _send)
    return sent


@pytest.fixture
def mailbox(monkeypatch):
    """The sign-in codes that would have been mailed."""
    sent = []

    async def _send(email, code, link):
        sent.append({"email": email, "code": code})

    monkeypatch.setattr(email_login.mailer, "send_login_mail", _send)
    return sent


def _user(db_session, email, **fields):
    """An account that is not signed in on the test client."""
    user = User(
        email=email,
        email_verified_at=datetime.now(timezone.utc),
        display_name=fields.pop("display_name", email.split("@")[0].title()),
        role=fields.pop("role", "viewer"),
        **fields,
    )
    db_session.add(user)
    db_session.commit()
    return user


def _resume(client, db_session, user):
    """Put ``client`` back on an account made earlier, with a new session."""
    now = datetime.now(timezone.utc)
    token = new_token()
    db_session.add(
        Session(
            token_hash=hash_token(token),
            user_id=user.id,
            provider="email",
            created_at=now,
            expires_at=now + timedelta(days=30),
            last_seen_at=now,
        )
    )
    db_session.commit()
    client.cookies.set("resslab_session", token)


async def _sign_in_by_mail(client, mailbox, email):
    await client.post("/auth/email/start", json={"email": email})
    return await client.post("/auth/email/verify", json={"code": mailbox[-1]["code"]})


# --- who gets in ------------------------------------------------------------
async def test_the_admin_routes_need_an_admin(client, sign_in):
    assert (await client.get("/admin/users")).status_code == 401
    sign_in(role="curator")
    for path in ("/admin/users", "/admin/invitations", "/admin/access-requests"):
        assert (await client.get(path)).status_code == 403


async def test_the_members_list_says_who_is_locked(
    client, sign_in, db_session, monkeypatch
):
    monkeypatch.setattr(roles.settings, "admin_emails", "boss@epfl.ch")
    _user(db_session, "boss@epfl.ch", role="admin", role_source="admin-email")
    _user(
        db_session,
        "dl@example.org",
        role="admin",
        role_source="github",
        github_login="dl",
        github_role="admin",
    )
    _user(db_session, "ada@example.com")
    sign_in(email="me@example.org", role="admin", role_override="admin")

    body = {item["email"]: item for item in (await client.get("/admin/users")).json()}
    assert body["boss@epfl.ch"]["locked"]
    assert body["dl@example.org"]["locked"]
    assert body["dl@example.org"]["github_role"] == "admin"
    assert not body["ada@example.com"]["locked"]
    # An admin the Hub made can be unmade by another admin.
    assert not body["me@example.org"]["locked"]


# --- changing a member ------------------------------------------------------
async def test_an_admin_sets_and_clears_a_role(client, sign_in, db_session):
    target = _user(db_session, "ada@example.com")
    sign_in(email="me@example.org", role="admin")

    response = await client.patch(
        f"/admin/users/{target.id}", json={"role_override": "curator"}
    )
    assert response.status_code == 200
    assert (response.json()["role"], response.json()["role_source"]) == (
        "curator",
        "override",
    )

    # null goes back to what the sources say: here, nothing.
    response = await client.patch(
        f"/admin/users/{target.id}", json={"role_override": None}
    )
    assert (response.json()["role"], response.json()["role_override"]) == (
        "viewer",
        None,
    )


async def test_a_field_that_is_not_sent_does_not_change(client, sign_in, db_session):
    target = _user(db_session, "ada@example.com", role_override="contributor")
    sign_in(email="me@example.org", role="admin")
    response = await client.patch(f"/admin/users/{target.id}", json={"disabled": False})
    assert response.json()["role_override"] == "contributor"


async def test_an_unknown_role_is_refused(client, sign_in, db_session):
    target = _user(db_session, "ada@example.com")
    sign_in(email="me@example.org", role="admin")
    response = await client.patch(
        f"/admin/users/{target.id}", json={"role_override": "owner"}
    )
    assert response.status_code == 422


async def test_an_admin_cannot_change_their_own_account(client, sign_in):
    me = sign_in(email="me@example.org", role="admin")
    response = await client.patch(f"/admin/users/{me.id}", json={"disabled": True})
    assert response.status_code == 403
    assert response.json()["detail"] == "cannot_change_self"


async def test_admins_from_github_or_the_config_are_out_of_reach(
    client, sign_in, db_session, monkeypatch
):
    monkeypatch.setattr(roles.settings, "admin_emails", "boss@epfl.ch")
    config_admin = _user(db_session, "boss@epfl.ch", role="admin")
    github_admin = _user(
        db_session,
        "dl@example.org",
        role="admin",
        github_login="dl",
        github_role="admin",
    )
    sign_in(email="me@example.org", role="admin")
    for target in (config_admin, github_admin):
        for change in ({"role_override": "viewer"}, {"disabled": True}):
            response = await client.patch(f"/admin/users/{target.id}", json=change)
            assert response.status_code == 403
            assert response.json()["detail"] == "locked_admin"


async def test_an_unknown_member_is_a_404(client, sign_in):
    sign_in(email="me@example.org", role="admin")
    response = await client.patch(
        "/admin/users/00000000-0000-0000-0000-000000000000", json={"disabled": True}
    )
    assert response.status_code == 404


async def test_disabling_signs_the_person_out_everywhere(client, sign_in, db_session):
    target = sign_in(email="ada@example.com")
    their_cookie = client.cookies.get("resslab_session")
    sign_in(email="me@example.org", role="admin")

    response = await client.patch(f"/admin/users/{target.id}", json={"disabled": True})
    assert response.json()["disabled"]

    sessions = db_session.execute(
        select(Session).where(Session.user_id == target.id)
    ).scalars()
    assert all(item.revoked_at is not None for item in sessions)
    client.cookies.set("resslab_session", their_cookie)
    assert (await client.get("/auth/me")).json() == {"user": None}


async def test_a_disabled_account_cannot_sign_in_again(client, mailbox, db_session):
    _user(db_session, "ada@example.com", disabled_at=datetime.now(timezone.utc))
    response = await _sign_in_by_mail(client, mailbox, "ada@example.com")
    assert response.status_code == 403
    assert response.json()["detail"] == "account_disabled"
    assert not client.cookies.get("resslab_session")


async def test_enabling_lets_the_person_back_in(client, mailbox, sign_in, db_session):
    target = _user(
        db_session, "ada@example.com", disabled_at=datetime.now(timezone.utc)
    )
    sign_in(email="me@example.org", role="admin")
    response = await client.patch(f"/admin/users/{target.id}", json={"disabled": False})
    assert not response.json()["disabled"]

    client.cookies.clear()
    assert (
        await _sign_in_by_mail(client, mailbox, "ada@example.com")
    ).status_code == 200


# --- invitations ------------------------------------------------------------
async def test_an_invitation_is_mailed_and_listed(client, sign_in, outbox):
    sign_in(email="me@example.org", role="admin", display_name="Pierre")
    response = await client.post(
        "/admin/invitations", json={"email": "Grace@Example.com", "role": "curator"}
    )
    assert response.status_code == 201
    body = response.json()
    assert (body["email"], body["role"], body["status"]) == (
        "grace@example.com",
        "curator",
        "pending",
    )
    assert body["mailed"] and body["invited_by"] == "Pierre"

    assert [mail["to"] for mail in outbox] == ["grace@example.com"]
    assert outbox[0]["link"].endswith("/login")
    assert "Pierre" in outbox[0]["body"][0]

    listed = (await client.get("/admin/invitations")).json()
    assert [item["email"] for item in listed] == ["grace@example.com"]


async def test_a_failed_mail_still_keeps_the_invitation(client, sign_in, monkeypatch):
    async def _refuse(*args, **kwargs):
        raise mailer.MailError("relay is down")

    monkeypatch.setattr(mailer, "send_notice", _refuse)
    sign_in(email="me@example.org", role="admin")
    response = await client.post(
        "/admin/invitations", json={"email": "grace@example.com"}
    )
    assert response.status_code == 201
    assert response.json()["mailed"] is False
    assert len((await client.get("/admin/invitations")).json()) == 1


async def test_one_open_invitation_per_address(client, sign_in, outbox):
    sign_in(email="me@example.org", role="admin")
    payload = {"email": "grace@example.com"}
    assert (await client.post("/admin/invitations", json=payload)).status_code == 201
    response = await client.post("/admin/invitations", json=payload)
    assert response.status_code == 409
    assert response.json()["detail"] == "already_invited"


async def test_a_member_is_not_invited(client, sign_in, db_session, outbox):
    _user(db_session, "ada@example.com")
    sign_in(email="me@example.org", role="admin")
    response = await client.post(
        "/admin/invitations", json={"email": "ada@example.com"}
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "already_member"
    assert outbox == []


async def test_an_added_address_is_a_member_too(client, sign_in, db_session, outbox):
    """The account is found by any of its addresses (#402)."""
    ada = _user(db_session, "ada@gmail.com")
    db_session.add(
        Identity(
            user_id=ada.id,
            provider="email",
            subject="ada@example.com",
            handle="ada@example.com",
        )
    )
    db_session.commit()
    sign_in(email="me@example.org", role="admin")
    response = await client.post(
        "/admin/invitations", json={"email": "ada@example.com"}
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "already_member"
    assert outbox == []


async def test_nobody_is_invited_as_a_viewer(client, sign_in):
    sign_in(email="me@example.org", role="admin")
    response = await client.post(
        "/admin/invitations", json={"email": "grace@example.com", "role": "viewer"}
    )
    assert response.status_code == 422


async def test_a_revoked_invitation_is_kept_but_closed(client, sign_in, outbox):
    sign_in(email="me@example.org", role="admin")
    created = (
        await client.post("/admin/invitations", json={"email": "grace@example.com"})
    ).json()

    assert (
        await client.delete(f"/admin/invitations/{created['id']}")
    ).status_code == 204
    assert (await client.get("/admin/invitations")).json()[0]["status"] == "revoked"
    # Gone from the pending ones, so a new invitation may be sent.
    assert (
        await client.delete(f"/admin/invitations/{created['id']}")
    ).status_code == 404
    response = await client.post(
        "/admin/invitations", json={"email": "grace@example.com"}
    )
    assert response.status_code == 201


async def test_the_invitation_is_redeemed_at_the_first_sign_in(
    client, mailbox, db_session
):
    db_session.add(Invitation(email="grace@example.com", role="curator"))
    db_session.commit()

    response = await _sign_in_by_mail(client, mailbox, "grace@example.com")
    user = response.json()["user"]
    assert (user["role"], user["role_source"]) == ("curator", "override")

    db_session.expire_all()
    invitation = db_session.execute(select(Invitation)).scalar_one()
    assert invitation.redeemed_at is not None
    assert invitation.redeemed_by == user["id"]


async def test_a_revoked_invitation_grants_nothing(client, mailbox, db_session):
    db_session.add(
        Invitation(
            email="grace@example.com",
            role="curator",
            revoked_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()
    response = await _sign_in_by_mail(client, mailbox, "grace@example.com")
    assert response.json()["user"]["role"] == "viewer"


# --- access requests --------------------------------------------------------
async def test_a_viewer_asks_and_an_admin_approves(client, sign_in, db_session, outbox):
    _user(db_session, "boss@example.org", role="admin")
    ada = sign_in(email="ada@example.com", institution="ACME labs")
    response = await client.post(
        "/auth/access-request", json={"message": "Brace tests from our lab."}
    )
    assert response.status_code == 201
    assert response.json()["status"] == "pending"

    # The account page can show that it is waiting.
    me = (await client.get("/auth/me")).json()["user"]
    assert me["access_request"]["status"] == "pending"
    # The admins heard about it, with the message.
    assert [mail["to"] for mail in outbox] == ["boss@example.org"]
    assert outbox[0]["body"][-1].endswith("Brace tests from our lab.")
    assert outbox[0]["link"].endswith("/admin")

    sign_in(email="me@example.org", role="admin")
    listed = (await client.get("/admin/access-requests")).json()
    assert [(item["email"], item["status"]) for item in listed] == [
        ("ada@example.com", "pending")
    ]
    response = await client.post(f"/admin/access-requests/{listed[0]['id']}/approve")
    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert response.json()["current_role"] == "contributor"

    db_session.expire_all()
    stored = db_session.get(User, ada.id)
    assert (stored.role, stored.role_source, stored.role_override) == (
        "contributor",
        "override",
        "contributor",
    )
    assert outbox[-1]["to"] == "ada@example.com"

    again = await client.post(f"/admin/access-requests/{listed[0]['id']}/approve")
    assert again.status_code == 409


async def test_one_open_request_at_a_time(client, sign_in, outbox):
    sign_in(email="ada@example.com")
    assert (await client.post("/auth/access-request", json={})).status_code == 201
    response = await client.post("/auth/access-request", json={})
    assert response.status_code == 409
    assert response.json()["detail"] == "already_pending"


async def test_after_a_decline_they_may_ask_again(client, sign_in, db_session, outbox):
    ada = sign_in(email="ada@example.com")
    await client.post("/auth/access-request", json={})
    request_id = db_session.execute(select(AccessRequest.id)).scalar_one()

    sign_in(email="me@example.org", role="admin")
    response = await client.post(f"/admin/access-requests/{request_id}/decline")
    assert response.json()["status"] == "declined"
    db_session.expire_all()
    assert db_session.get(User, ada.id).role == "viewer"
    # No mail for a no.
    assert all(mail["to"] != "ada@example.com" for mail in outbox)

    _resume(client, db_session, ada)
    me = (await client.get("/auth/me")).json()["user"]
    assert me["access_request"]["status"] == "declined"
    assert (await client.post("/auth/access-request", json={})).status_code == 201


async def test_nothing_to_ask_for_a_contributor(client, sign_in):
    sign_in(email="ada@epfl.ch", role="contributor")
    response = await client.post("/auth/access-request", json={})
    assert response.status_code == 409
    assert response.json()["detail"] == "already_granted"


async def test_asking_needs_a_verified_address(client, sign_in):
    sign_in(email="ada@example.com", verified=False)
    response = await client.post("/auth/access-request", json={})
    assert response.status_code == 409
    assert response.json()["detail"] == "email_required"


async def test_approving_never_lowers_a_role(client, sign_in, db_session):
    """A curator through GitHub stays one, the request just closes."""
    curator = _user(
        db_session,
        "ada@example.com",
        role="curator",
        role_source="github",
        github_login="ada",
        github_role="write",
        github_role_synced_at=datetime.now(timezone.utc),
    )
    item = AccessRequest(user_id=curator.id, role="contributor", status="pending")
    db_session.add(item)
    db_session.commit()

    sign_in(email="me@example.org", role="admin")
    response = await client.post(f"/admin/access-requests/{item.id}/approve")
    assert response.json()["current_role"] == "curator"
    db_session.expire_all()
    assert db_session.get(User, curator.id).role_override is None


# --- merging two accounts (#402) ---------------------------------------------
def _identity(db_session, user, provider, subject):
    db_session.add(
        Identity(user_id=user.id, provider=provider, subject=subject, handle=subject)
    )
    db_session.commit()


def _two_accounts(db_session):
    """One person: an EPFL code account and a GitHub one with a gmail."""
    keep = _user(db_session, "ada@epfl.ch", display_name="Ada", institution="")
    _identity(db_session, keep, "email", "ada@epfl.ch")
    other = _user(
        db_session,
        "ada.l@gmail.com",
        display_name="Ada L",
        institution="EPFL",
        github_login="ada",
        github_role="write",
    )
    _identity(db_session, other, "email", "ada.l@gmail.com")
    _identity(db_session, other, "github", "4242")
    return keep, other


async def test_an_admin_merges_two_accounts_of_one_person(
    client, sign_in, mailbox, db_session
):
    keep, other = _two_accounts(db_session)
    keep_id, other_id = keep.id, other.id
    _resume(client, db_session, other)
    their_cookie = client.cookies.get("resslab_session")
    sign_in(email="me@example.org", role="admin")

    response = await client.post(
        f"/admin/users/{keep_id}/merge", json={"from_user_id": other_id}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == keep_id
    assert body["email"] == "ada@epfl.ch"
    assert body["emails"] == ["ada@epfl.ch", "ada.l@gmail.com"]
    assert body["github_login"] == "ada"
    assert body["institution"] == "EPFL"
    assert body["display_name"] == "Ada"
    # Write access on the data repo, now on the kept account.
    assert body["role"] == "curator"

    db_session.expire_all()
    assert db_session.get(User, other_id) is None
    moved = db_session.execute(
        select(Identity.provider, Identity.subject).where(Identity.user_id == keep_id)
    ).all()
    assert sorted(moved) == [
        ("email", "ada.l@gmail.com"),
        ("email", "ada@epfl.ch"),
        ("github", "4242"),
    ]
    # The other account's browser is signed out.
    client.cookies.set("resslab_session", their_cookie)
    assert (await client.get("/auth/me")).json() == {"user": None}
    # Its address now signs in to the kept account.
    client.cookies.clear()
    signed = await _sign_in_by_mail(client, mailbox, "ada.l@gmail.com")
    assert signed.json()["user"]["id"] == keep_id


async def test_an_admin_merges_their_other_account_into_their_own(
    client, sign_in, db_session
):
    me = sign_in(email="me@epfl.ch", role="admin", role_override="admin")
    old = _user(db_session, "me@gmail.com")
    _identity(db_session, old, "email", "me@gmail.com")

    response = await client.post(
        f"/admin/users/{me.id}/merge", json={"from_user_id": old.id}
    )
    assert response.status_code == 200
    assert response.json()["emails"] == ["me@epfl.ch", "me@gmail.com"]
    # Still signed in.
    assert (await client.get("/auth/me")).json()["user"]["id"] == me.id


async def test_an_admin_cannot_merge_their_own_account_away(
    client, sign_in, db_session
):
    keep = _user(db_session, "ada@epfl.ch")
    me = sign_in(email="me@example.org", role="admin")
    response = await client.post(
        f"/admin/users/{keep.id}/merge", json={"from_user_id": me.id}
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "cannot_change_self"


async def test_merges_that_are_refused(client, sign_in, db_session):
    keep, other = _two_accounts(db_session)
    third = _user(db_session, "ada@example.com", github_login="ada2")
    _identity(db_session, third, "github", "777")
    gone = _user(db_session, "old@example.com", disabled_at=datetime.now(timezone.utc))
    sign_in(email="me@example.org", role="admin")

    async def merge(keep_id, other_id):
        return await client.post(
            f"/admin/users/{keep_id}/merge", json={"from_user_id": other_id}
        )

    cases = [
        (keep.id, keep.id, 409, "same_account"),
        (other.id, third.id, 409, "both_github"),
        (keep.id, gone.id, 409, "account_disabled"),
        (keep.id, "00000000-0000-0000-0000-000000000000", 404, "not_found"),
    ]
    for keep_id, other_id, code, detail in cases:
        response = await merge(keep_id, other_id)
        assert (response.status_code, response.json()["detail"]) == (code, detail)
    db_session.expire_all()
    assert db_session.get(User, third.id) is not None


async def test_a_merge_keeps_the_strongest_decision_and_one_open_request(
    client, sign_in, db_session
):
    keep = _user(db_session, "ada@epfl.ch", role_override="contributor")
    other = _user(db_session, "ada@gmail.com", role_override="curator")
    for user in (keep, other):
        db_session.add(AccessRequest(user_id=user.id, role="contributor"))
    db_session.commit()
    keep_id = keep.id
    sign_in(email="me@example.org", role="admin")

    response = await client.post(
        f"/admin/users/{keep_id}/merge", json={"from_user_id": other.id}
    )
    assert response.status_code == 200
    assert response.json()["role_override"] == "curator"
    db_session.expire_all()
    statuses = db_session.execute(
        select(AccessRequest.status).where(AccessRequest.user_id == keep_id)
    ).scalars()
    assert sorted(statuses) == ["declined", "pending"]
