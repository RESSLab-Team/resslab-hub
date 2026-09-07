"""
The sign-in flows, over HTTP.

Auth is enforced by FastAPI dependencies, which only run for real requests, so
everything here goes through the ``client`` fixture rather than calling the
endpoint functions.
"""

import aiosmtplib
import pytest
from sqlalchemy import select, text

from resslab_hub.auth import email_login, github_oauth, mailer
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

    monkeypatch.setattr(mailer, "send_login_mail", _send)
    monkeypatch.setattr(email_login.mailer, "send_login_mail", _send)
    return sent


@pytest.fixture
def broken_relay(monkeypatch):
    """A configured relay that refuses every mail, through the real mailer."""

    async def _send(message, **kwargs):
        raise aiosmtplib.SMTPAuthenticationError(535, "denied")

    monkeypatch.setattr(mailer.settings, "smtp_host", "mail.example")
    monkeypatch.setattr(mailer.aiosmtplib, "send", _send)


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
    client, broken_relay, db_session, monkeypatch
):
    """A dead relay must not cost the person their five mails per hour."""
    for _ in range(email_login.MAX_MAILS_PER_HOUR + 1):
        response = await client.post(
            "/auth/email/start", json={"email": "ada@example.edu"}
        )
        assert response.status_code == 503
        assert response.json()["detail"] == "mail_failed"
        assert not response.cookies.get("resslab_login")

    # Nothing was written, so nothing counts against the caps.
    assert db_session.execute(select(LoginChallenge)).scalars().all() == []

    # And once the relay is back, the address can still ask for a code.
    monkeypatch.setattr(mailer.settings, "smtp_host", None)
    await _start(client, redirect_to="/")
    assert len(db_session.execute(select(LoginChallenge)).scalars().all()) == 1


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


async def test_the_email_identity_cannot_be_unlinked(client, sign_in, db_session):
    """The account is found by its address, so removing the row would only
    pretend the address no longer signs in."""
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
    identity = db_session.execute(select(Identity)).scalar_one()
    # The immutable numeric id, not the login, which people rename.
    assert (identity.provider, identity.subject) == ("github", "4242")


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


async def test_curation_queue_opens_for_a_signed_in_user(client, sign_in):
    sign_in()
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
