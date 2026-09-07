"""Pure-unit tests for the sign-in building blocks (no database)."""

import logging

import aiosmtplib
import pytest

from resslab_hub.auth import mailer, roles, tokens, urls
from resslab_hub.auth.users import name_from_email, normalize_email
from resslab_hub.models.database.auth import User


# --- tokens ---------------------------------------------------------------
def test_code_is_six_digits():
    for _ in range(50):
        code = tokens.new_code()
        assert len(code) == 6
        assert code.isdigit()


def test_tokens_are_unique_and_long():
    values = {tokens.new_token() for _ in range(100)}
    assert len(values) == 100
    assert all(len(value) >= 40 for value in values)


def test_matches_only_the_right_value():
    code = "123456"
    stored = tokens.hash_token(code)
    assert tokens.matches(code, stored)
    assert not tokens.matches("123457", stored)
    # An empty presented value or an empty stored hash never matches, so a
    # challenge row with a null hash cannot be opened with "".
    assert not tokens.matches("", stored)
    assert not tokens.matches(code, "")


# --- redirect safety ------------------------------------------------------
@pytest.mark.parametrize(
    "target",
    [
        "https://evil.example/steal",
        "//evil.example/steal",
        "/\\evil.example",
        "javascript:alert(1)",
        "",
        "contribute",
    ],
)
def test_off_site_redirects_are_refused(target):
    assert urls.safe_redirect(target) == "/"


@pytest.mark.parametrize(
    "target",
    ["/", "/contribute/new", "/curation/12", "/account?tab=identities"],
)
def test_own_paths_are_kept(target):
    assert urls.safe_redirect(target) == target


# --- roles ----------------------------------------------------------------
def test_role_ordering():
    assert roles.at_least("admin", "viewer")
    assert roles.at_least("curator", "contributor")
    assert roles.at_least("viewer", "viewer")
    assert not roles.at_least("contributor", "curator")
    # An unknown role ranks lowest rather than blowing up.
    assert not roles.at_least("nonsense", "contributor")


def test_override_wins_over_everything(monkeypatch):
    monkeypatch.setattr(roles.settings, "admin_emails", "boss@epfl.ch")
    user = User(
        email="boss@epfl.ch", email_verified_at=object(), role_override="viewer"
    )
    assert roles.derive_role(user) == ("viewer", "override")


def test_admin_email_grants_admin_at_sign_in(monkeypatch):
    from datetime import datetime, timezone

    monkeypatch.setattr(roles.settings, "admin_emails", "Boss@EPFL.ch, other@x.edu")
    user = User(email="boss@epfl.ch", email_verified_at=datetime.now(timezone.utc))
    assert roles.derive_role(user) == ("admin", "admin-email")


def test_admin_email_needs_a_verified_address(monkeypatch):
    monkeypatch.setattr(roles.settings, "admin_emails", "boss@epfl.ch")
    user = User(email="boss@epfl.ch", email_verified_at=None)
    assert roles.derive_role(user) == ("viewer", "default")


def test_signed_in_without_a_grant_is_a_viewer(monkeypatch):
    from datetime import datetime, timezone

    monkeypatch.setattr(roles.settings, "admin_emails", "")
    user = User(
        email="someone@example.edu", email_verified_at=datetime.now(timezone.utc)
    )
    assert roles.derive_role(user) == ("viewer", "default")


# --- users ----------------------------------------------------------------
def test_email_normalisation():
    assert normalize_email("  Ada@EPFL.CH ") == "ada@epfl.ch"


def test_display_name_guessed_from_the_address():
    assert name_from_email("ada.lovelace@epfl.ch") == "Ada Lovelace"
    assert name_from_email("dlignos@epfl.ch") == "Dlignos"


# --- mail -----------------------------------------------------------------
def test_message_carries_the_code_the_link_and_a_display_name(monkeypatch):
    monkeypatch.setattr(mailer.settings, "smtp_from", "noreply+resslab-hub@epfl.ch")
    link = "http://127.0.0.1:5173/login/verify?challenge=abc&token=xyz"
    message = mailer.build_message("ada@example.edu", "123456", link)

    assert message["From"] == "RESSLab Hub <noreply+resslab-hub@epfl.ch>"
    assert message["To"] == "ada@example.edu"
    assert "123456" in message["Subject"]
    body = message.get_content()
    assert "123456" in body
    assert link in body


async def test_without_a_host_the_code_goes_to_the_log(monkeypatch, caplog):
    monkeypatch.setattr(mailer.settings, "smtp_host", None)
    caplog.set_level(logging.WARNING, logger="resslab_hub.auth.mailer")

    await mailer.send_login_mail("ada@example.edu", "123456", "http://x/verify")

    assert "123456" in caplog.text
    assert "http://x/verify" in caplog.text


async def test_the_send_uses_starttls_and_a_short_timeout(monkeypatch):
    seen = {}

    async def _send(message, **kwargs):
        seen.update(kwargs)

    monkeypatch.setattr(mailer.settings, "smtp_host", "mail.example")
    monkeypatch.setattr(mailer.settings, "smtp_starttls", True)
    monkeypatch.setattr(mailer.aiosmtplib, "send", _send)

    await mailer.send_login_mail("ada@example.edu", "123456", "http://x/verify")

    assert seen["hostname"] == "mail.example"
    assert seen["start_tls"] is True
    assert seen["timeout"] == mailer.TIMEOUT_SECONDS


async def test_a_refusing_relay_becomes_a_mail_error(monkeypatch, caplog):
    async def _send(message, **kwargs):
        raise aiosmtplib.SMTPConnectError("relay is down")

    monkeypatch.setattr(mailer.settings, "smtp_host", "mail.example")
    monkeypatch.setattr(mailer.aiosmtplib, "send", _send)
    caplog.set_level(logging.ERROR, logger="resslab_hub.auth.mailer")

    with pytest.raises(mailer.MailError):
        await mailer.send_login_mail("ada@example.edu", "123456", "http://x/verify")

    # The reason is logged, the code never is.
    assert "relay is down" in caplog.text
    assert "123456" not in caplog.text
