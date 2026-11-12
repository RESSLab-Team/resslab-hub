"""
The sign-in flows, over HTTP.

Auth is enforced by FastAPI dependencies, which only run for real requests, so
everything here goes through the ``client`` fixture rather than calling the
endpoint functions.
"""

import json
import logging
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit

import aiosmtplib
import pytest
from sqlalchemy import select, text

from resslab_hub.auth import email_login, github_oauth, mailer, orcid_oauth
from resslab_hub.models.database.auth import Identity, LoginChallenge, Session, User
from resslab_hub.utils.rate_limit import limiter
from tests.conftest import SERVICE_AUTH


@pytest.fixture(autouse=True)
def _no_rate_limits(monkeypatch):
    monkeypatch.setattr(limiter, "enabled", False)


@pytest.fixture
def mailbox(monkeypatch):
    """Capture what would have been mailed, instead of sending it."""
    sent = []

    async def _send(email, code, link):
        sent.append({"email": email, "code": code, "link": link})

    async def _send_add(email, code):
        sent.append({"email": email, "code": code, "link": None})

    monkeypatch.setattr(mailer, "send_login_mail", _send)
    monkeypatch.setattr(email_login.mailer, "send_login_mail", _send)
    monkeypatch.setattr(email_login.mailer, "send_add_email_mail", _send_add)
    return sent


@pytest.fixture
def broken_relay(monkeypatch):
    """A configured relay that refuses every mail, through the real mailer."""

    async def _send(message, **kwargs):
        raise aiosmtplib.SMTPAuthenticationError(535, "denied")

    monkeypatch.setattr(mailer.settings, "smtp_host", "mail.example")
    monkeypatch.setattr(mailer.aiosmtplib, "send", _send)


@pytest.fixture
def no_relay_in_a_deployment(monkeypatch):
    """A deployment where nobody set SMTP_HOST (#247)."""
    monkeypatch.setattr(mailer.settings, "smtp_host", None)
    monkeypatch.setattr(mailer.settings, "deployment", "stage")


async def _start(client, email="ada@example.edu", redirect_to="/contribute/new"):
    response = await client.post(
        "/auth/email/start", json={"email": email, "redirect_to": redirect_to}
    )
    assert response.status_code == 200
    assert response.json() == {"sent": True}
    return response


# --- who am I -------------------------------------------------------------
async def test_me_is_anonymous_not_an_error(client):
    response = await client.get("/auth/me")
    assert response.status_code == 200
    assert response.json() == {"user": None}
    # Never cached: this answer is different for every visitor.
    assert response.headers["cache-control"] == "no-store"


async def test_me_reports_the_signed_in_user(client, sign_in):
    sign_in(email="ada@example.edu", role="curator")
    body = (await client.get("/auth/me")).json()["user"]
    assert body["email"] == "ada@example.edu"
    assert body["role"] == "curator"
    assert [item["provider"] for item in body["identities"]] == ["email"]


# --- signing in by mail ---------------------------------------------------
async def test_code_sign_in_creates_the_account(client, mailbox, db_session):
    await _start(client)
    assert mailbox[0]["email"] == "ada@example.edu"

    response = await client.post(
        "/auth/email/verify", json={"code": mailbox[0]["code"]}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["email"] == "ada@example.edu"
    assert payload["user"]["role"] == "viewer"
    # The name is guessed from the address so the account is not nameless.
    assert payload["user"]["display_name"] == "Ada"
    assert payload["redirect_to"] == "/contribute/new"
    assert client.cookies.get("resslab_session")

    user = db_session.execute(select(User)).scalar_one()
    assert user.email_verified_at is not None
    identity = db_session.execute(select(Identity)).scalar_one()
    assert (identity.provider, identity.subject) == ("email", "ada@example.edu")

    # And the session is now usable.
    assert (await client.get("/auth/me")).json()["user"]["email"] == "ada@example.edu"


async def test_an_academic_address_becomes_a_contributor(client, mailbox):
    """The grant that lets someone submit, end to end (#248)."""
    await _start(client, email="ada@epfl.ch")
    response = await client.post(
        "/auth/email/verify", json={"code": mailbox[0]["code"]}
    )
    user = response.json()["user"]
    assert user["role"] == "contributor"
    assert user["role_source"] == "academic-email"


async def test_a_free_mailbox_stays_a_viewer(client, mailbox):
    await _start(client, email="ada@gmail.com")
    response = await client.post(
        "/auth/email/verify", json={"code": mailbox[0]["code"]}
    )
    user = response.json()["user"]
    assert user["role"] == "viewer"
    assert user["role_source"] == "default"


async def test_signing_in_twice_reuses_the_account(client, mailbox, db_session):
    for _ in range(2):
        await _start(client)
        assert (
            await client.post("/auth/email/verify", json={"code": mailbox[-1]["code"]})
        ).status_code == 200
    assert len(db_session.execute(select(User)).scalars().all()) == 1
    assert len(db_session.execute(select(Identity)).scalars().all()) == 1


async def test_the_mailed_link_works_without_the_cookie(client, mailbox):
    await _start(client)
    link = mailbox[0]["link"]
    challenge = link.split("challenge=")[1].split("&")[0]
    token = link.split("token=")[1]
    client.cookies.clear()

    response = await client.post(
        "/auth/email/verify", json={"challenge": challenge, "token": token}
    )
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "ada@example.edu"


async def test_a_code_works_only_once(client, mailbox):
    await _start(client)
    code = mailbox[0]["code"]
    assert (
        await client.post("/auth/email/verify", json={"code": code})
    ).status_code == 200
    # A replay of the same code, even with the cookie still around, is dead.
    second = await client.post("/auth/email/verify", json={"code": code})
    assert second.status_code == 400
    assert second.json()["detail"] == "invalid_or_expired"


async def test_five_wrong_codes_kill_the_challenge(client, mailbox):
    await _start(client)
    for _ in range(4):
        response = await client.post("/auth/email/verify", json={"code": "000000"})
        assert response.json()["detail"] == "invalid_code"
    fifth = await client.post("/auth/email/verify", json={"code": "000000"})
    assert fifth.json()["detail"] == "too_many_attempts"
    # Even the right code no longer helps.
    real = await client.post("/auth/email/verify", json={"code": mailbox[0]["code"]})
    assert real.status_code == 400


async def test_an_expired_code_is_refused(client, mailbox, db_session):
    await _start(client)
    db_session.execute(
        text("UPDATE auth_login_challenge SET expires_at = NOW() - INTERVAL '1 hour'")
    )
    db_session.commit()
    response = await client.post(
        "/auth/email/verify", json={"code": mailbox[0]["code"]}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_or_expired"


async def test_an_address_cannot_be_mail_bombed(client, mailbox, db_session):
    for _ in range(email_login.MAX_MAILS_PER_HOUR + 3):
        await _start(client)
    assert len(mailbox) == email_login.MAX_MAILS_PER_HOUR
    # Capped, but the answer never says so.
    assert len(db_session.execute(select(LoginChallenge)).scalars().all()) == 5


async def test_a_broken_relay_does_not_burn_the_rate_limit(
    client, broken_relay, db_session, monkeypatch, caplog
):
    """A dead relay must not cost the person their five mails per hour."""
    caplog.set_level(logging.ERROR, logger="resslab_hub.auth.mailer")
    for _ in range(email_login.MAX_MAILS_PER_HOUR + 1):
        response = await client.post(
            "/auth/email/start", json={"email": "ada@example.edu"}
        )
        assert response.status_code == 503
        assert response.json()["detail"] == "mail_failed"
        assert not response.cookies.get("resslab_login")

    # The SMTP reason is in the server log, for whoever has to fix it.
    assert "SMTPAuthenticationError" in caplog.text
    assert "denied" in caplog.text

    # Nothing was written, so nothing counts against the caps.
    assert db_session.execute(select(LoginChallenge)).scalars().all() == []

    # And once the relay is back, the address can still ask for a code.
    monkeypatch.setattr(mailer.settings, "smtp_host", None)
    monkeypatch.setattr(mailer.settings, "deployment", None)
    await _start(client, redirect_to="/")
    assert len(db_session.execute(select(LoginChallenge)).scalars().all()) == 1


async def test_a_deployment_without_a_relay_says_so(
    client, no_relay_in_a_deployment, db_session
):
    """#247: the page said "we sent a code" and the code went to the log."""
    response = await client.post("/auth/email/start", json={"email": "ada@epfl.ch"})

    assert response.status_code == 503
    assert response.json()["detail"] == "mail_not_configured"
    assert not response.cookies.get("resslab_login")
    assert db_session.execute(select(LoginChallenge)).scalars().all() == []


async def test_one_ip_cannot_mail_bomb_a_list_of_people(client, mailbox):
    cap = email_login.MAX_MAILS_PER_HOUR_PER_IP
    for index in range(cap + 3):
        await _start(client, email=f"person{index}@example.edu")
    assert len(mailbox) == cap


async def test_old_challenges_are_purged_when_a_new_one_starts(
    client, mailbox, db_session
):
    await _start(client)
    db_session.execute(
        text("UPDATE auth_login_challenge SET expires_at = NOW() - INTERVAL '2 days'")
    )
    db_session.commit()
    await _start(client, email="bob@example.edu")
    rows = db_session.execute(select(LoginChallenge)).scalars().all()
    assert [row.email for row in rows] == ["bob@example.edu"]


async def test_an_off_site_redirect_is_dropped(client, mailbox):
    await _start(client, redirect_to="https://evil.example/steal")
    response = await client.post(
        "/auth/email/verify", json={"code": mailbox[0]["code"]}
    )
    assert response.json()["redirect_to"] == "/"


async def test_admin_emails_bootstrap_an_administrator(client, mailbox, monkeypatch):
    from resslab_hub.auth import roles

    monkeypatch.setattr(roles.settings, "admin_emails", "ada@example.edu")
    await _start(client)
    response = await client.post(
        "/auth/email/verify", json={"code": mailbox[0]["code"]}
    )
    assert response.json()["user"]["role"] == "admin"
    assert response.json()["user"]["role_source"] == "admin-email"


# --- signing out ----------------------------------------------------------
async def test_logout_drops_the_session(client, sign_in, db_session):
    sign_in()
    assert (await client.post("/auth/logout")).status_code == 204
    assert db_session.execute(select(Session)).scalars().all() == []
    assert (await client.get("/auth/me")).json() == {"user": None}


async def test_logout_without_a_session_is_fine(client):
    assert (await client.post("/auth/logout")).status_code == 204


async def test_a_revoked_session_stops_working(client, sign_in, db_session):
    sign_in()
    db_session.execute(text("UPDATE auth_session SET revoked_at = NOW()"))
    db_session.commit()
    assert (await client.get("/auth/me")).json() == {"user": None}


async def test_an_expired_session_is_cleaned_up(client, sign_in, db_session):
    sign_in()
    db_session.execute(
        text("UPDATE auth_session SET expires_at = NOW() - INTERVAL '1 day'")
    )
    db_session.commit()
    assert (await client.get("/auth/me")).json() == {"user": None}
    assert db_session.execute(select(Session)).scalars().all() == []


async def test_a_disabled_account_cannot_use_its_session(client, sign_in, db_session):
    sign_in()
    db_session.execute(text("UPDATE auth_user SET disabled_at = NOW()"))
    db_session.commit()
    assert (await client.get("/auth/me")).json() == {"user": None}


# --- identities -----------------------------------------------------------
async def test_the_only_identity_cannot_be_unlinked(client, sign_in, db_session):
    sign_in()
    identity = db_session.execute(select(Identity)).scalar_one()
    response = await client.delete(f"/auth/identities/{identity.id}")
    assert response.status_code == 409


async def test_a_second_identity_can_be_unlinked(client, sign_in, db_session):
    user = sign_in()
    db_session.add(
        Identity(user_id=user.id, provider="github", subject="4242", handle="ada")
    )
    db_session.execute(text("UPDATE auth_user SET github_login = 'ada'"))
    db_session.commit()

    github = db_session.execute(
        select(Identity).where(Identity.provider == "github")
    ).scalar_one()
    assert (await client.delete(f"/auth/identities/{github.id}")).status_code == 204
    remaining = db_session.execute(select(Identity)).scalars().all()
    assert [item.provider for item in remaining] == ["email"]
    # The mirrored login goes with it, so nothing claims a link that is gone.
    db_session.expire_all()
    assert db_session.execute(select(User)).scalar_one().github_login == ""


async def test_the_main_address_cannot_be_removed(client, sign_in, db_session):
    """It signs new submissions and gets the mails: pick another one first."""
    user = sign_in()
    db_session.add(
        Identity(user_id=user.id, provider="github", subject="4242", handle="ada")
    )
    db_session.commit()
    email = db_session.execute(
        select(Identity).where(Identity.provider == "email")
    ).scalar_one()
    response = await client.delete(f"/auth/identities/{email.id}")
    assert response.status_code == 409
    assert response.json()["detail"] == "cannot_unlink"


async def test_identities_need_a_session(client):
    assert (await client.get("/auth/identities")).status_code == 401


# --- several addresses (#402) ---------------------------------------------
async def _add(client, mailbox, email):
    """Ask for the code, then type it. Returns the verify response."""
    response = await client.post("/auth/emails", json={"email": email})
    assert response.status_code == 200, response.text
    assert response.json() == {"sent": True}
    mail = mailbox[-1]
    assert mail["email"] == email.lower()
    assert mail["link"] is None  # a code only, see docs/auth.md
    return await client.post("/auth/emails/verify", json={"code": mail["code"]})


def _addresses(body):
    return sorted(
        item["handle"] for item in body["identities"] if item["provider"] == "email"
    )


async def test_an_added_address_makes_a_contributor(client, sign_in, mailbox):
    """The case of the issue: a gmail account adds its EPFL address."""
    sign_in(email="ada@gmail.com")
    response = await _add(client, mailbox, "Ada.Lovelace@EPFL.ch")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["email"] == "ada@gmail.com"  # the main one does not move
    assert _addresses(body) == ["ada.lovelace@epfl.ch", "ada@gmail.com"]
    assert body["role"] == "contributor"
    assert body["role_source"] == "academic-email"

    me = (await client.get("/auth/me")).json()["user"]
    assert _addresses(me) == ["ada.lovelace@epfl.ch", "ada@gmail.com"]


async def test_an_added_address_signs_in_to_the_same_account(client, sign_in, mailbox):
    user = sign_in(email="ada@gmail.com")
    await _add(client, mailbox, "ada@epfl.ch")
    client.cookies.clear()

    await _start(client, email="ada@epfl.ch")
    response = await client.post(
        "/auth/email/verify", json={"code": mailbox[-1]["code"]}
    )
    assert response.status_code == 200, response.text
    assert response.json()["user"]["id"] == user.id
    assert response.json()["user"]["email"] == "ada@gmail.com"


async def test_an_address_of_another_account_is_refused(
    client, sign_in, mailbox, db_session
):
    """Two accounts are never joined, even when one person owns both."""
    other = sign_in(email="ada@epfl.ch")
    client.cookies.clear()
    sign_in(email="ada@gmail.com")
    response = await _add(client, mailbox, "ada@epfl.ch")
    assert response.status_code == 409
    assert response.json()["detail"] == "email_in_use"
    owners = (
        db_session.execute(
            select(Identity.user_id).where(Identity.subject == "ada@epfl.ch")
        )
        .scalars()
        .all()
    )
    assert owners == [other.id]


async def test_an_address_already_yours_is_refused_at_once(client, sign_in, mailbox):
    sign_in(email="ada@gmail.com")
    response = await client.post("/auth/emails", json={"email": "ADA@gmail.com"})
    assert response.status_code == 409
    assert response.json()["detail"] == "already_yours"
    assert mailbox == []


async def test_adding_an_address_needs_a_session(client, mailbox):
    assert (
        await client.post("/auth/emails", json={"email": "ada@epfl.ch"})
    ).status_code == 401
    assert (
        await client.post("/auth/emails/verify", json={"code": "123456"})
    ).status_code == 401


async def test_an_add_email_code_never_signs_in(client, sign_in, mailbox):
    """Someone who got the code still cannot open a session with it."""
    sign_in(email="ada@gmail.com")
    await client.post("/auth/emails", json={"email": "ada@epfl.ch"})
    login_cookie = client.cookies.get("resslab_login")
    client.cookies.clear()
    client.cookies.set("resslab_login", login_cookie)

    response = await client.post(
        "/auth/email/verify", json={"code": mailbox[-1]["code"]}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_or_expired"
    assert not client.cookies.get("resslab_session")


async def test_an_add_email_code_works_only_for_the_account_that_asked(
    client, sign_in, mailbox
):
    sign_in(email="ada@gmail.com")
    await client.post("/auth/emails", json={"email": "ada@epfl.ch"})
    login_cookie = client.cookies.get("resslab_login")

    client.cookies.clear()
    sign_in(email="eve@gmail.com")
    client.cookies.set("resslab_login", login_cookie)
    response = await client.post(
        "/auth/emails/verify", json={"code": mailbox[-1]["code"]}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_or_expired"


async def test_a_sign_in_code_cannot_add_an_address(client, sign_in, mailbox):
    """The other way round: a sign-in challenge is not an add-email one."""
    await _start(client, email="ada@epfl.ch")
    login_cookie = client.cookies.get("resslab_login")
    sign_in(email="eve@gmail.com")
    client.cookies.set("resslab_login", login_cookie)
    response = await client.post(
        "/auth/emails/verify", json={"code": mailbox[-1]["code"]}
    )
    assert response.status_code == 400


async def test_a_wrong_add_email_code_is_refused(client, sign_in, mailbox):
    sign_in(email="ada@gmail.com")
    await client.post("/auth/emails", json={"email": "ada@epfl.ch"})
    response = await client.post("/auth/emails/verify", json={"code": "000000"})
    if mailbox[-1]["code"] == "000000":  # one chance in a million
        return
    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_code"


async def test_a_github_account_without_an_address_gets_a_main_one(
    client, sign_in, mailbox, db_session
):
    """A GitHub account with a private mail could not submit before."""
    user = sign_in(email=None, provider="github", verified=False)
    response = await _add(client, mailbox, "ada@epfl.ch")
    assert response.status_code == 200, response.text
    assert response.json()["email"] == "ada@epfl.ch"
    assert response.json()["email_verified"] is True
    db_session.expire_all()
    stored = db_session.get(User, user.id)
    assert stored.email_verified_at is not None


async def test_the_main_address_can_be_changed(client, sign_in, mailbox, db_session):
    sign_in(email="ada@gmail.com")
    await _add(client, mailbox, "ada@epfl.ch")
    epfl = db_session.execute(
        select(Identity).where(Identity.subject == "ada@epfl.ch")
    ).scalar_one()
    response = await client.post(f"/auth/identities/{epfl.id}/main")
    assert response.status_code == 204
    me = (await client.get("/auth/me")).json()["user"]
    assert me["email"] == "ada@epfl.ch"

    # The old main one can go now, and the role stays: the EPFL address is
    # still there.
    gmail = db_session.execute(
        select(Identity).where(Identity.subject == "ada@gmail.com")
    ).scalar_one()
    assert (await client.delete(f"/auth/identities/{gmail.id}")).status_code == 204
    me = (await client.get("/auth/me")).json()["user"]
    assert _addresses(me) == ["ada@epfl.ch"]
    assert me["role"] == "contributor"


async def test_only_an_own_address_can_be_main(client, sign_in, db_session):
    ada = sign_in(email="ada@gmail.com")
    address = db_session.execute(select(Identity)).scalar_one()
    db_session.add(Identity(user_id=ada.id, provider="github", subject="1", handle="a"))
    db_session.commit()
    github = db_session.execute(
        select(Identity).where(Identity.provider == "github")
    ).scalar_one()
    # Not an address.
    assert (await client.post(f"/auth/identities/{github.id}/main")).status_code == 404

    client.cookies.clear()
    sign_in(email="eve@gmail.com")
    # Not this account's.
    response = await client.post(f"/auth/identities/{address.id}/main")
    assert response.status_code == 404


async def test_removing_the_academic_address_drops_the_role(
    client, sign_in, mailbox, db_session
):
    """A role worked out from an address goes with it. An override stays."""
    sign_in(email="ada@gmail.com")
    await _add(client, mailbox, "ada@epfl.ch")
    epfl = db_session.execute(
        select(Identity).where(Identity.subject == "ada@epfl.ch")
    ).scalar_one()
    assert (await client.delete(f"/auth/identities/{epfl.id}")).status_code == 204
    me = (await client.get("/auth/me")).json()["user"]
    assert me["role"] == "viewer"
    # Gone from the account, so it no longer finds it.
    client.cookies.clear()
    await _start(client, email="ada@epfl.ch")
    response = await client.post(
        "/auth/email/verify", json={"code": mailbox[-1]["code"]}
    )
    assert response.json()["user"]["email"] == "ada@epfl.ch"
    assert len(db_session.execute(select(User)).scalars().all()) == 2


async def test_an_invitation_waits_for_an_added_address(
    client, sign_in, mailbox, db_session
):
    from resslab_hub.models.database.auth import Invitation

    db_session.add(Invitation(email="ada@lab.example", role="curator"))
    db_session.commit()
    sign_in(email="ada@gmail.com")
    response = await _add(client, mailbox, "ada@lab.example")
    assert response.json()["role"] == "curator"


# --- GitHub ---------------------------------------------------------------
@pytest.fixture
def github(monkeypatch):
    """Enable GitHub sign-in and fake the two calls that leave the process."""
    monkeypatch.setattr(github_oauth.settings, "github_oauth_client_id", "cid")
    monkeypatch.setattr(github_oauth.settings, "github_oauth_client_secret", "secret")

    profile = github_oauth.GitHubProfile(
        subject="4242",
        login="ada",
        name="Ada Lovelace",
        email="ada@example.edu",
        email_verified=True,
    )

    async def _fetch(code):
        assert code == "the-code"
        return profile

    monkeypatch.setattr(github_oauth, "fetch_profile", _fetch)
    import resslab_hub.routers.auth as auth_router

    monkeypatch.setattr(auth_router.github_oauth, "fetch_profile", _fetch)
    return profile


async def test_github_start_goes_back_to_login_when_disabled(client, monkeypatch):
    # A navigation, not a fetch: a JSON 503 would be shown raw in the tab.
    monkeypatch.setattr(github_oauth.settings, "github_oauth_client_id", None)
    monkeypatch.setattr(github_oauth.settings, "github_oauth_client_secret", None)
    response = await client.get("/auth/github/start")
    assert response.status_code == 302
    assert response.headers["location"].endswith("/login?error=github_disabled")
    assert "resslab_login" not in response.headers.get("set-cookie", "")


async def _github_state(client):
    response = await client.get(
        "/auth/github/start", params={"redirect_to": "/contribute/new"}
    )
    assert response.status_code == 302
    location = response.headers["location"]
    assert location.startswith("https://github.com/login/oauth/authorize")
    return location.split("state=")[1].split("&")[0]


async def test_github_sign_in_creates_the_account(client, github, db_session):
    state = await _github_state(client)
    response = await client.get(
        "/auth/github/callback", params={"code": "the-code", "state": state}
    )
    assert response.status_code == 302
    assert response.headers["location"].endswith("/contribute/new")
    assert client.cookies.get("resslab_session")

    user = db_session.execute(select(User)).scalar_one()
    assert user.github_login == "ada"
    assert user.email == "ada@example.edu"
    identities = {
        item.provider: item.subject
        for item in db_session.execute(select(Identity)).scalars().all()
    }
    # The immutable numeric id, not the login, which people rename. And the
    # proven address is one of the account's addresses, like any other (#402).
    assert identities == {"github": "4242", "email": "ada@example.edu"}


async def test_github_sign_in_returns_to_the_same_account(client, github, db_session):
    for _ in range(2):
        state = await _github_state(client)
        await client.get(
            "/auth/github/callback", params={"code": "the-code", "state": state}
        )
    assert len(db_session.execute(select(User)).scalars().all()) == 1


async def test_a_state_cannot_be_replayed(client, github):
    state = await _github_state(client)
    assert (
        await client.get(
            "/auth/github/callback", params={"code": "the-code", "state": state}
        )
    ).status_code == 302
    replay = await client.get(
        "/auth/github/callback", params={"code": "the-code", "state": state}
    )
    assert "error=github_failed" in replay.headers["location"]


async def test_the_callback_only_works_in_the_browser_that_started_it(
    client, github, db_session
):
    """Login CSRF: an attacker finishes GitHub's side, then sends the callback
    URL to someone else. Their browser has no resslab_login cookie."""
    state = await _github_state(client)
    client.cookies.clear()
    response = await client.get(
        "/auth/github/callback", params={"code": "the-code", "state": state}
    )
    assert "error=github_failed" in response.headers["location"]
    assert not client.cookies.get("resslab_session")
    assert db_session.execute(select(User)).scalars().all() == []


async def test_github_errors_are_mapped_not_echoed(client, github):
    state = await _github_state(client)
    response = await client.get(
        "/auth/github/callback",
        params={"state": state, "code": "x", "error": "foo&next=/admin#x"},
    )
    location = response.headers["location"]
    assert location.endswith("/login?error=github_failed")

    state = await _github_state(client)
    response = await client.get(
        "/auth/github/callback",
        params={"state": state, "error": "access_denied"},
    )
    assert response.headers["location"].endswith("/login?error=github_denied")


async def test_an_unknown_state_is_refused(client, github):
    response = await client.get(
        "/auth/github/callback",
        params={"code": "the-code", "state": "00000000-0000-0000-0000-000000000000"},
    )
    assert "error=github_failed" in response.headers["location"]


async def test_github_never_takes_over_an_existing_address(
    client, github, sign_in, db_session
):
    """The whole point of not merging on a matching mail."""
    sign_in(email="ada@example.edu")
    client.cookies.clear()  # the attacker is not signed in as her

    state = await _github_state(client)
    response = await client.get(
        "/auth/github/callback", params={"code": "the-code", "state": state}
    )
    assert "error=email_in_use" in response.headers["location"]
    assert not client.cookies.get("resslab_session")
    assert len(db_session.execute(select(User)).scalars().all()) == 1


async def test_linking_github_while_signed_in(client, github, sign_in, db_session):
    user = sign_in(email="ada@example.edu")
    response = await client.get(
        "/auth/github/start", params={"link": True, "redirect_to": "/account"}
    )
    state = response.headers["location"].split("state=")[1].split("&")[0]

    callback = await client.get(
        "/auth/github/callback", params={"code": "the-code", "state": state}
    )
    assert callback.status_code == 302
    assert callback.headers["location"].endswith("/account")

    db_session.expire_all()
    stored = db_session.execute(select(User)).scalar_one()
    assert stored.github_login == "ada"
    providers = sorted(
        item.provider for item in db_session.execute(select(Identity)).scalars().all()
    )
    assert providers == ["email", "github"]
    assert stored.id == user.id


async def test_github_sign_in_with_write_access_makes_a_curator(
    client, github, github_permissions, db_session
):
    """Write (or maintain) on the data repo is the curator role (#248)."""
    github_permissions["ada"] = "write"
    state = await _github_state(client)
    await client.get(
        "/auth/github/callback", params={"code": "the-code", "state": state}
    )

    user = db_session.execute(select(User)).scalar_one()
    assert (user.role, user.role_source) == ("curator", "github")
    assert user.github_role == "write"
    assert user.github_role_synced_at is not None


async def test_linking_github_with_admin_access_makes_an_admin(
    client, github, github_permissions, sign_in, db_session
):
    """No need to wait for the next sign-in to get the role."""
    github_permissions["ada"] = "admin"
    sign_in(email="ada@example.edu")
    response = await client.get("/auth/github/start", params={"link": True})
    state = response.headers["location"].split("state=")[1].split("&")[0]
    await client.get(
        "/auth/github/callback", params={"code": "the-code", "state": state}
    )

    db_session.expire_all()
    user = db_session.execute(select(User)).scalar_one()
    assert (user.role, user.role_source) == ("admin", "github")


async def test_the_role_follows_github_within_the_hour(
    client, sign_in, github_permissions, db_session
):
    """Access removed on GitHub: the first request after an hour drops it."""
    from datetime import datetime, timedelta, timezone

    sign_in(
        role="curator",
        role_source="github",
        github_login="ada",
        github_role="write",
        github_role_synced_at=datetime.now(timezone.utc) - timedelta(hours=2),
    )
    github_permissions["ada"] = "read"

    body = (await client.get("/auth/me")).json()["user"]
    assert (body["role"], body["role_source"]) == ("viewer", "default")
    db_session.expire_all()
    assert db_session.execute(select(User)).scalar_one().github_role == "read"


async def test_a_fresh_permission_is_kept(client, sign_in, github_permissions):
    from datetime import datetime, timedelta, timezone

    sign_in(
        role="curator",
        role_source="github",
        github_login="ada",
        github_role="write",
        github_role_synced_at=datetime.now(timezone.utc) - timedelta(minutes=10),
    )
    github_permissions["ada"] = "none"
    assert (await client.get("/auth/me")).json()["user"]["role"] == "curator"


async def test_email_sign_in_reads_the_linked_github_again(
    client, mailbox, github_permissions, db_session
):
    from datetime import datetime, timezone

    db_session.add(
        User(
            email="ada@example.edu",
            email_verified_at=datetime.now(timezone.utc),
            display_name="Ada",
            role="curator",
            github_login="ada",
            github_role="write",
            github_role_synced_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()
    github_permissions["ada"] = "none"

    await _start(client)
    response = await client.post(
        "/auth/email/verify", json={"code": mailbox[0]["code"]}
    )
    assert response.json()["user"]["role"] == "viewer"


async def test_linking_a_github_account_someone_else_owns(
    client, github, sign_in, db_session
):
    # Someone else already signed in with that GitHub account.
    owner = User(email="owner@example.edu", display_name="Owner")
    db_session.add(owner)
    db_session.flush()
    db_session.add(
        Identity(user_id=owner.id, provider="github", subject="4242", handle="ada")
    )
    db_session.commit()

    sign_in(email="thief@example.edu")
    response = await client.get("/auth/github/start", params={"link": True})
    state = response.headers["location"].split("state=")[1].split("&")[0]
    callback = await client.get(
        "/auth/github/callback", params={"code": "the-code", "state": state}
    )
    assert "error=identity_taken" in callback.headers["location"]


async def test_linking_needs_a_session(client, github):
    assert (
        await client.get("/auth/github/start", params={"link": True})
    ).status_code == 401


# --- what the machine credential still reaches ----------------------------
async def test_user_probe_stays_on_the_machine_credential(client):
    """The data repo's workflows call this before uploading; keep it working."""
    assert (await client.get("/user")).status_code == 401
    ok = await client.get("/user", auth=SERVICE_AUTH)
    assert ok.status_code == 200
    assert ok.json() == {"username": SERVICE_AUTH[0]}


async def test_a_session_is_not_a_machine_credential(client, sign_in):
    sign_in(role="admin")
    # /user and /upload are the ingestion path, not something a person drives.
    assert (await client.get("/user")).status_code == 401


async def test_a_wrong_password_is_refused(client):
    response = await client.get("/user", auth=("user", "wrong"))
    assert response.status_code == 401
    # Speaking Basic gets the Basic challenge back, so curl -f reports cleanly.
    assert response.headers.get("www-authenticate") == "Basic"


async def test_no_basic_challenge_for_a_browser(client):
    """A 401 must not pop the browser's own password dialog."""
    response = await client.get("/auth/identities")
    assert response.status_code == 401
    assert "www-authenticate" not in response.headers


# --- the endpoints that changed hands -------------------------------------
async def test_curation_queue_needs_a_session(client):
    assert (await client.get("/contributions")).status_code == 401


async def test_the_curation_queue_is_for_curators(client, sign_in):
    """The lab's work list (#248). A contributor reads only their own PR."""
    sign_in(email="ada@epfl.ch", role="contributor")
    assert (await client.get("/contributions")).status_code == 403


async def test_curation_queue_opens_for_a_curator(client, sign_in):
    sign_in(role="curator")
    # 200 with configured=false when no GitHub App is set up: past the gate,
    # which is what this asserts.
    assert (await client.get("/contributions")).status_code == 200


async def _submit(client):
    return await client.post(
        "/contributions",
        params={"type": "all-braces"},
        files={"file": ("batch.tar.gz", b"x", "application/gzip")},
    )


async def _update(client):
    return await client.put(
        "/contributions/7",
        data={"head_sha": "a" * 40},
        files={"file": ("batch.tar.gz", b"x", "application/gzip")},
    )


async def test_submitting_needs_a_session(client):
    assert (await _submit(client)).status_code == 401


async def test_updating_a_submission_needs_a_session(client):
    assert (await _update(client)).status_code == 401


async def test_a_viewer_cannot_submit(client, sign_in):
    """Signed in is not permission to open a pull request on the data repo."""
    sign_in(email="ada@example.com")
    assert (await _submit(client)).status_code == 403
    assert (await _update(client)).status_code == 403


async def test_a_contributor_is_past_the_gate(client, sign_in):
    sign_in(email="ada@epfl.ch", role="contributor")
    # The archive is junk, so this fails later on. What matters is that it
    # is no longer refused by the role gate.
    for response in (await _submit(client), await _update(client)):
        assert response.status_code not in (401, 403)


async def test_a_full_review_queue_refuses_new_submissions(
    client, sign_in, monkeypatch
):
    """A backstop on open submissions, whatever the rate limit (#264 H4)."""
    from resslab_hub.routers import contributions as contributions_router

    pulls = [{"head_ref": f"contrib/braces/b{i}-x"} for i in range(3)]

    async def fake_open_pulls(_client):
        return pulls

    monkeypatch.setattr(contributions_router, "configured", lambda: True)
    monkeypatch.setattr(contributions_router, "DataRepoClient", lambda: None)
    monkeypatch.setattr(contributions_router, "open_pulls", fake_open_pulls)
    monkeypatch.setattr(contributions_router.settings, "max_open_contributions", 3)
    sign_in(email="ada@epfl.ch", role="contributor")

    response = await _submit(client)
    assert response.status_code == 503
    assert "queue is full" in response.json()["detail"]
    # An update opens no pull request: it is not refused for that.
    assert (await _update(client)).status_code != 503

    # Verification pull requests are the curators' own, they do not count.
    pulls[:] = [{"head_ref": f"verify/braces/v{i}-x"} for i in range(3)]
    # Past the backstop: the junk archive is what fails now.
    assert (await _submit(client)).status_code == 400


async def test_too_many_dismissed_warnings_are_refused(client, sign_in):
    sign_in(email="ada@epfl.ch", role="contributor")
    response = await client.post(
        "/contributions",
        params={"type": "all-braces"},
        data={"dismissed_warnings": json.dumps(["w"] * 101)},
        files={"file": ("batch.tar.gz", b"x", "application/gzip")},
    )
    assert response.status_code == 400
    assert "Too many" in response.json()["detail"]


# --- /validate has two kinds of caller ------------------------------------
def _tiny_targz() -> bytes:
    """An archive that fails validation, which is fine: we test the gate."""
    import io
    import tarfile

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        info = tarfile.TarInfo("braces/steel_braces.csv")
        payload = b"id\nB1\n"
        info.size = len(payload)
        tar.addfile(info, io.BytesIO(payload))
    return buffer.getvalue()


def _archive_upload():
    return {"file": ("c.tar.gz", _tiny_targz(), "application/gzip")}


async def test_validate_is_closed_to_strangers(client):
    response = await client.post(
        "/validate", params={"type": "all-braces"}, files=_archive_upload()
    )
    assert response.status_code == 401


async def test_validate_accepts_the_data_repo_ci(client):
    response = await client.post(
        "/validate",
        params={"type": "all-braces"},
        files=_archive_upload(),
        auth=SERVICE_AUTH,
    )
    assert response.status_code == 200


async def test_validate_accepts_any_signed_in_account(client, sign_in):
    """A viewer cannot submit yet, but must be able to check their data."""
    sign_in(role="viewer")
    response = await client.post(
        "/validate", params={"type": "all-braces"}, files=_archive_upload()
    )
    assert response.status_code == 200


async def test_upload_stays_on_the_machine_credential(client, sign_in):
    sign_in(role="admin")
    response = await client.post(
        "/upload", params={"type": "all-braces"}, files=_archive_upload()
    )
    assert response.status_code == 401


# --- cross-site writes ----------------------------------------------------
async def test_a_cross_site_post_with_our_cookie_is_refused(client, sign_in):
    sign_in()
    response = await client.post(
        "/auth/logout", headers={"sec-fetch-site": "cross-site"}
    )
    assert response.status_code == 403


async def test_a_cross_site_post_without_a_cookie_is_refused_too(client):
    """The sign-in endpoints have no cookie yet and are the login-CSRF target."""
    response = await client.post(
        "/auth/email/start",
        json={"email": "ada@example.edu"},
        headers={"sec-fetch-site": "cross-site"},
    )
    assert response.status_code == 403


async def test_our_own_pages_can_post(client, sign_in):
    sign_in()
    response = await client.post(
        "/auth/logout", headers={"sec-fetch-site": "same-origin"}
    )
    assert response.status_code == 204


# --- ORCID (#250) ---------------------------------------------------------

ORCID_ID = "0000-0002-1825-0097"


@pytest.fixture
def orcid(monkeypatch):
    """Enable ORCID sign-in and fake the one call that leaves the process."""
    monkeypatch.setattr(orcid_oauth.settings, "orcid_client_id", "APP-CID")
    monkeypatch.setattr(orcid_oauth.settings, "orcid_client_secret", "secret")
    monkeypatch.setattr(orcid_oauth.settings, "orcid_sandbox", True)
    profile = orcid_oauth.OrcidProfile(subject=ORCID_ID, name="Ada Lovelace")

    async def _fetch(code):
        assert code == "the-code"
        return profile

    monkeypatch.setattr(orcid_oauth, "fetch_profile", _fetch)
    return profile


async def _orcid_state(client, redirect_to="/contribute/new", link=False):
    params = {"redirect_to": redirect_to}
    if link:
        params["link"] = True
    response = await client.get("/auth/orcid/start", params=params)
    assert response.status_code == 302
    location = response.headers["location"]
    assert location.startswith("https://sandbox.orcid.org/oauth/authorize")
    return parse_qs(urlsplit(location).query)["state"][0]


async def _orcid(client, **kwargs):
    """The whole round trip; returns the callback response."""
    state = await _orcid_state(client, **kwargs)
    response = await client.get(
        "/auth/orcid/callback", params={"code": "the-code", "state": state}
    )
    assert response.status_code == 302
    return response


def _orcid_owner(db_session, subject=ORCID_ID):
    return db_session.execute(
        select(Identity.user_id).where(
            Identity.provider == "orcid", Identity.subject == subject
        )
    ).scalar_one()


async def _me(client):
    return (await client.get("/auth/me")).json()["user"]


async def test_orcid_start_goes_back_to_login_when_disabled(client, monkeypatch):
    monkeypatch.setattr(orcid_oauth.settings, "orcid_client_id", None)
    monkeypatch.setattr(orcid_oauth.settings, "orcid_client_secret", None)
    response = await client.get("/auth/orcid/start")
    assert response.status_code == 302
    assert response.headers["location"].endswith("/login?error=orcid_disabled")
    assert "resslab_login" not in response.headers.get("set-cookie", "")


async def test_first_orcid_sign_in_asks_for_an_address(client, orcid, db_session):
    response = await _orcid(client)
    assert response.headers["location"].endswith(
        "/account?add_email=1&next=%2Fcontribute%2Fnew"
    )
    assert client.cookies.get("resslab_session")

    user = db_session.execute(select(User)).scalar_one()
    assert user.email is None
    assert user.orcid == ORCID_ID
    assert user.display_name == "Ada Lovelace"
    assert user.role == "viewer"
    identities = db_session.execute(select(Identity)).scalars().all()
    assert [(item.provider, item.subject) for item in identities] == [
        ("orcid", ORCID_ID)
    ]


async def test_the_second_orcid_sign_in_goes_straight_on(client, orcid, db_session):
    await _orcid(client)
    client.cookies.clear()
    response = await _orcid(client)
    # Even with no address yet: the person was asked once, and skipped.
    assert response.headers["location"].endswith("/contribute/new")
    assert len(db_session.execute(select(User)).scalars().all()) == 1


async def test_a_private_orcid_name_shows_the_id(client, orcid, db_session):
    orcid.name = ""
    await _orcid(client)
    assert db_session.execute(select(User)).scalar_one().display_name == ORCID_ID


async def test_orcid_then_a_new_address(client, orcid, mailbox):
    await _orcid(client)
    user_id = (await _me(client))["id"]
    response = await _add(client, mailbox, "ada@epfl.ch")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == user_id
    assert body["email"] == "ada@epfl.ch"
    assert body["role"] == "contributor"


async def test_orcid_then_the_address_of_an_account_joins_it(
    client, orcid, sign_in, mailbox, db_session
):
    """The person had a mail account and clicked ORCID first: one account."""
    existing = sign_in(email="ada@epfl.ch", role="contributor")
    client.cookies.clear()
    await _orcid(client)
    bare_id = (await _me(client))["id"]
    assert bare_id != existing.id

    response = await _add(client, mailbox, "ada@epfl.ch")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == existing.id
    assert body["orcid"] == ORCID_ID
    assert sorted(item["provider"] for item in body["identities"]) == [
        "email",
        "orcid",
    ]
    # This browser is signed in there now; the bare account is gone.
    assert (await _me(client))["id"] == existing.id
    assert [row.id for row in db_session.execute(select(User)).scalars()] == [
        existing.id
    ]
    assert _orcid_owner(db_session) == existing.id

    # And ORCID opens that account from now on.
    client.cookies.clear()
    response = await _orcid(client)
    assert response.headers["location"].endswith("/contribute/new")
    assert (await _me(client))["id"] == existing.id


async def test_no_join_when_the_orcid_account_has_an_address(
    client, orcid, sign_in, mailbox, db_session
):
    sign_in(email="ada@epfl.ch")
    client.cookies.clear()
    await _orcid(client)
    assert (await _add(client, mailbox, "ada@gmail.com")).status_code == 200
    response = await _add(client, mailbox, "ada@epfl.ch")
    assert response.status_code == 409
    assert response.json()["detail"] == "email_in_use"
    assert len(db_session.execute(select(User)).scalars().all()) == 2


async def test_no_join_into_an_account_with_another_orcid(
    client, orcid, sign_in, mailbox, db_session
):
    existing = sign_in(email="ada@epfl.ch")
    db_session.add(
        Identity(
            user_id=existing.id,
            provider="orcid",
            subject="0000-0001-5109-3700",
            handle="0000-0001-5109-3700",
        )
    )
    db_session.commit()
    client.cookies.clear()
    await _orcid(client)
    response = await _add(client, mailbox, "ada@epfl.ch")
    assert response.status_code == 409
    assert response.json()["detail"] == "email_in_use"
    assert _orcid_owner(db_session) != existing.id


async def test_no_join_into_a_disabled_account(
    client, orcid, sign_in, mailbox, db_session
):
    sign_in(email="ada@epfl.ch", disabled_at=datetime.now(timezone.utc))
    client.cookies.clear()
    await _orcid(client)
    response = await _add(client, mailbox, "ada@epfl.ch")
    assert response.status_code == 403
    assert response.json()["detail"] == "account_disabled"
    assert len(db_session.execute(select(User)).scalars().all()) == 2


async def test_a_disabled_orcid_account_cannot_sign_in(client, orcid, db_session):
    await _orcid(client)
    db_session.execute(text("UPDATE auth_user SET disabled_at = now()"))
    db_session.commit()
    client.cookies.clear()
    response = await _orcid(client)
    assert response.headers["location"].endswith("/login?error=account_disabled")
    assert not client.cookies.get("resslab_session")


async def test_an_orcid_state_cannot_be_replayed(client, orcid):
    state = await _orcid_state(client)
    params = {"code": "the-code", "state": state}
    await client.get("/auth/orcid/callback", params=params)
    replay = await client.get("/auth/orcid/callback", params=params)
    assert "error=orcid_failed" in replay.headers["location"]


async def test_the_orcid_callback_only_works_in_the_browser_that_started_it(
    client, orcid, db_session
):
    state = await _orcid_state(client)
    client.cookies.clear()
    response = await client.get(
        "/auth/orcid/callback", params={"code": "the-code", "state": state}
    )
    assert "error=orcid_failed" in response.headers["location"]
    assert not client.cookies.get("resslab_session")
    assert db_session.execute(select(User)).scalars().all() == []


async def test_a_state_only_finishes_on_its_own_provider(client, github, orcid):
    state = await _github_state(client)
    response = await client.get(
        "/auth/orcid/callback", params={"code": "the-code", "state": state}
    )
    assert "error=orcid_failed" in response.headers["location"]

    state = await _orcid_state(client)
    response = await client.get(
        "/auth/github/callback", params={"code": "the-code", "state": state}
    )
    assert "error=github_failed" in response.headers["location"]


async def test_orcid_errors_are_mapped_not_echoed(client, orcid, monkeypatch):
    state = await _orcid_state(client)
    response = await client.get(
        "/auth/orcid/callback",
        params={"state": state, "code": "x", "error": "foo&next=/admin#x"},
    )
    assert response.headers["location"].endswith("/login?error=orcid_failed")

    state = await _orcid_state(client)
    response = await client.get(
        "/auth/orcid/callback", params={"state": state, "error": "access_denied"}
    )
    assert response.headers["location"].endswith("/login?error=orcid_denied")

    async def _broken(code):
        raise orcid_oauth.OrcidOAuthError("invalid_grant")

    monkeypatch.setattr(orcid_oauth, "fetch_profile", _broken)
    state = await _orcid_state(client)
    response = await client.get(
        "/auth/orcid/callback", params={"state": state, "code": "the-code"}
    )
    assert response.headers["location"].endswith("/login?error=orcid_failed")


async def test_linking_orcid_while_signed_in(client, orcid, sign_in, db_session):
    user = sign_in(email="ada@example.edu", orcid="0000-0000-0000-0000")
    response = await _orcid(client, redirect_to="/account", link=True)
    assert response.headers["location"].endswith("/account")

    db_session.expire_all()
    stored = db_session.execute(select(User)).scalar_one()
    assert stored.id == user.id
    # A proved iD wins over a typed one.
    assert stored.orcid == ORCID_ID
    assert _orcid_owner(db_session) == user.id


async def test_linking_an_orcid_of_a_bare_account_joins_it(
    client, orcid, sign_in, db_session
):
    """ORCID once, skipped the address, then signed in by mail and linked."""
    await _orcid(client)
    client.cookies.clear()
    user = sign_in(email="ada@epfl.ch")
    response = await _orcid(client, redirect_to="/account", link=True)
    assert response.headers["location"].endswith("/account")
    assert [row.id for row in db_session.execute(select(User)).scalars()] == [user.id]
    assert _orcid_owner(db_session) == user.id


async def test_linking_an_orcid_someone_else_owns(client, orcid, sign_in, db_session):
    owner = sign_in(email="owner@epfl.ch")
    db_session.add(
        Identity(user_id=owner.id, provider="orcid", subject=ORCID_ID, handle=ORCID_ID)
    )
    db_session.commit()
    client.cookies.clear()
    sign_in(email="ada@gmail.com")
    response = await _orcid(client, redirect_to="/account", link=True)
    assert response.headers["location"].endswith("/account?error=identity_taken")
    assert _orcid_owner(db_session) == owner.id


async def test_unlinking_orcid_clears_the_id(client, orcid, sign_in, db_session):
    sign_in(email="ada@example.edu")
    await _orcid(client, redirect_to="/account", link=True)
    identity = db_session.execute(
        select(Identity).where(Identity.provider == "orcid")
    ).scalar_one()
    assert (await client.delete(f"/auth/identities/{identity.id}")).status_code == 204
    db_session.expire_all()
    assert db_session.execute(select(User)).scalar_one().orcid == ""
