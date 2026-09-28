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


def test_academic_addresses_are_recognised(monkeypatch):
    monkeypatch.setattr(roles.settings, "contributor_domains", "")
    # On the pyswot list.
    assert roles.is_academic("ada@epfl.ch")
    assert roles.is_academic("ada@ethz.ch")
    assert roles.is_academic("ada@u-tokyo.ac.jp")
    # A subdomain matches its institution.
    assert roles.is_academic("ada@cs.stanford.edu")
    # Free mailboxes never pass, and the list is an allowlist: a domain it
    # does not know is not academic, whatever its ending.
    assert not roles.is_academic("ada@gmail.com")
    assert not roles.is_academic("ada@example.com")
    assert not roles.is_academic("ada@example.edu")
    # Nothing to read.
    assert not roles.is_academic("")
    assert not roles.is_academic("nobody")


def test_configured_domains_fill_the_gaps(monkeypatch):
    """The list knows universities, not research institutes or industry."""
    monkeypatch.setattr(roles.settings, "contributor_domains", "empa.ch, AISC.org")
    assert roles.is_academic("ada@empa.ch")
    assert roles.is_academic("ada@aisc.org")
    # Case and whitespace in the setting do not matter.
    assert roles.is_academic("Ada@AISC.org")
    # A subdomain of a configured one matches.
    assert roles.is_academic("ada@lab.empa.ch")
    # But a neighbour does not.
    assert not roles.is_academic("ada@notempa.ch")


def test_a_configured_tld_cannot_grant_a_whole_country(monkeypatch):
    monkeypatch.setattr(roles.settings, "contributor_domains", "ch")
    assert not roles.is_academic("ada@example.ch")


def test_academic_email_grants_contributor(monkeypatch):
    from datetime import datetime, timezone

    monkeypatch.setattr(roles.settings, "admin_emails", "")
    monkeypatch.setattr(roles.settings, "contributor_domains", "")
    user = User(email="ada@epfl.ch", email_verified_at=datetime.now(timezone.utc))
    assert roles.derive_role(user) == ("contributor", "academic-email")


def test_an_unverified_academic_address_grants_nothing(monkeypatch):
    monkeypatch.setattr(roles.settings, "admin_emails", "")
    monkeypatch.setattr(roles.settings, "contributor_domains", "")
    user = User(email="ada@epfl.ch", email_verified_at=None)
    assert roles.derive_role(user) == ("viewer", "default")


def test_admin_email_beats_the_academic_grant(monkeypatch):
    from datetime import datetime, timezone

    monkeypatch.setattr(roles.settings, "admin_emails", "ada@epfl.ch")
    monkeypatch.setattr(roles.settings, "contributor_domains", "")
    user = User(email="ada@epfl.ch", email_verified_at=datetime.now(timezone.utc))
    assert roles.derive_role(user) == ("admin", "admin-email")


def test_override_beats_the_academic_grant(monkeypatch):
    from datetime import datetime, timezone

    monkeypatch.setattr(roles.settings, "admin_emails", "")
    monkeypatch.setattr(roles.settings, "contributor_domains", "")
    user = User(
        email="ada@epfl.ch",
        email_verified_at=datetime.now(timezone.utc),
        role_override="viewer",
    )
    assert roles.derive_role(user) == ("viewer", "override")


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
LINK = "http://127.0.0.1:5173/login/verify?challenge=abc&token=xyz"


def _parts(message):
    """The text and html bodies of the multipart/alternative message."""
    by_type = {part.get_content_type(): part for part in message.walk()}
    return by_type["text/plain"].get_content(), by_type["text/html"].get_content()


def test_message_carries_the_code_the_link_and_a_display_name(monkeypatch):
    monkeypatch.setattr(mailer.settings, "smtp_from", "noreply-enacitdev@epfl.ch")
    message = mailer.build_message("ada@example.edu", "123456", LINK)

    assert message["From"] == "RESSLab Hub <noreply-enacitdev@epfl.ch>"
    assert message["To"] == "ada@example.edu"
    assert "123456" in message["Subject"]


def test_the_mail_has_a_text_part_and_an_html_part():
    message = mailer.build_message("ada@example.edu", "123456", LINK)
    assert message.get_content_type() == "multipart/alternative"

    text, html = _parts(message)
    # Text first, the html and its images second: the last part is the
    # preferred one.
    assert [p.get_content_type() for p in message.iter_parts()] == [
        "text/plain",
        "multipart/related",
    ]
    for body in (text, html):
        assert "123456" in body
        assert str(mailer.settings.login_code_ttl_minutes) in body
    assert LINK in text


def test_the_html_escapes_the_ampersand_in_the_link():
    """The link joins its two parameters with "&", twice in the html."""
    _, html = _parts(mailer.build_message("ada@example.edu", "123456", LINK))

    assert "challenge=abc&amp;token=xyz" in html
    # The raw form would cut the token off in a browser.
    assert "challenge=abc&token=xyz" not in html
    # Both the button and the copy-paste line carry it.
    assert html.count("challenge=abc&amp;token=xyz") >= 2


def test_no_placeholder_is_left_unfilled():
    text, html = _parts(mailer.build_message("ada@example.edu", "123456", LINK))
    for name in ("{code}", "{link}", "{ttl_minutes}"):
        assert name not in text
        assert name not in html


def test_the_html_keeps_its_css_braces():
    """The fill is str.replace, not str.format, so the style block survives."""
    _, html = _parts(mailer.build_message("ada@example.edu", "123456", LINK))
    assert "@media (prefers-color-scheme: dark)" in html
    assert "background-color:#171717 !important" in html


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


def test_the_logos_travel_with_the_mail():
    """Gmail and Outlook strip inline SVG, so the marks are attached images."""
    message = mailer.build_message("ada@example.edu", "123456", LINK)
    images = [p for p in message.walk() if p.get_content_type() == "image/png"]

    assert [p["Content-ID"] for p in images] == [
        "<rl-mark-light>",
        "<rl-mark-dark>",
        "<rl-epfl>",
    ]
    # Inline, so no client shows them as attachments to download.
    assert all(p.get_content_disposition() == "inline" for p in images)
    assert all(p.get_payload(decode=True) for p in images)

    # And the html asks for exactly those three.
    _, html = _parts(message)
    for content_id in mailer.LOGOS:
        assert f'src="cid:{content_id}"' in html


def test_the_card_is_not_capped_at_600px():
    """Asked for: the mail fills the window on a laptop."""
    _, html = _parts(mailer.build_message("ada@example.edu", "123456", LINK))
    assert "max-width:600px" not in html
    # The Outlook-only wrapper that forced 600px is gone with it.
    assert "[if mso]><table" not in html
