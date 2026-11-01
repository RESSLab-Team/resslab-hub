"""Pure-unit tests for the sign-in building blocks (no database)."""

import logging

import aiosmtplib
import pytest

from resslab_hub.auth import access, mailer, roles, tokens, urls
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


def test_the_config_admin_cannot_be_overridden(monkeypatch):
    """Nobody demotes from the Hub an admin the config made (#248)."""
    monkeypatch.setattr(roles.settings, "admin_emails", "boss@epfl.ch")
    user = User(
        email="boss@epfl.ch", email_verified_at=object(), role_override="viewer"
    )
    assert roles.derive_role(user) == ("admin", "admin-email")
    assert roles.is_locked_admin(user)


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


# --- roles from GitHub (#248) ---------------------------------------------
def _github_user(permission, **fields):
    return User(
        email=fields.pop("email", "ada@gmail.com"),
        email_verified_at=object(),
        github_login=fields.pop("github_login", "ada-l"),
        github_role=permission,
        **fields,
    )


@pytest.fixture
def no_config_grants(monkeypatch):
    monkeypatch.setattr(roles.settings, "admin_emails", "")
    monkeypatch.setattr(roles.settings, "contributor_domains", "")


def test_admin_on_the_data_repo_is_admin(no_config_grants):
    user = _github_user("admin", role_override="viewer")
    assert roles.derive_role(user) == ("admin", "github")
    assert roles.is_locked_admin(user)


def test_write_on_the_data_repo_is_curator(no_config_grants):
    user = _github_user("write")
    assert roles.derive_role(user) == ("curator", "github")
    assert not roles.is_locked_admin(user)


def test_the_override_beats_write_access(no_config_grants):
    """An admin can still demote a curator GitHub made, or promote one."""
    assert roles.derive_role(_github_user("write", role_override="viewer")) == (
        "viewer",
        "override",
    )
    user = _github_user("write", role_override="admin")
    assert roles.derive_role(user) == ("admin", "override")
    assert not roles.is_locked_admin(user)


@pytest.mark.parametrize("permission", ["read", "none", None, "triage"])
def test_read_access_grants_nothing(no_config_grants, permission):
    assert roles.derive_role(_github_user(permission)) == ("viewer", "default")
    user = _github_user(permission, email="ada@epfl.ch")
    assert roles.derive_role(user) == ("contributor", "academic-email")


def test_a_permission_without_a_login_is_ignored(no_config_grants):
    """Unlinking GitHub clears both, but never trust one without the other."""
    assert roles.derive_role(_github_user("admin", github_login="")) == (
        "viewer",
        "default",
    )


# --- GitHub permission sync ------------------------------------------------
@pytest.fixture
def github_permission(monkeypatch, no_config_grants):
    """What the fake data repo answers; an exception is raised instead."""
    from resslab_hub.auth import github_sync

    answer = {"value": "write", "calls": 0}

    class _FakeClient:
        async def get_permission(self, login):
            answer["calls"] += 1
            if isinstance(answer["value"], Exception):
                raise answer["value"]
            return answer["value"]

    monkeypatch.setattr(github_sync, "configured", lambda: True)
    monkeypatch.setattr(github_sync, "DataRepoClient", _FakeClient)
    return answer


def _ago(**delta):
    from datetime import datetime, timedelta, timezone

    return datetime.now(timezone.utc) - timedelta(**delta)


def test_a_permission_goes_stale_after_an_hour():
    from resslab_hub.auth import github_sync

    assert github_sync.is_stale(_github_user("write"))
    assert not github_sync.is_stale(
        _github_user("write", github_role_synced_at=_ago(minutes=10))
    )
    assert github_sync.is_stale(
        _github_user("write", github_role_synced_at=_ago(minutes=61))
    )
    # Nothing to read without a GitHub account.
    assert not github_sync.is_stale(_github_user(None, github_login=""))


async def test_a_sync_reads_the_permission_and_sets_the_role(github_permission):
    from resslab_hub.auth import github_sync

    user = _github_user(None, id="u1")
    await github_sync.refresh_github_role(user)
    assert (user.github_role, user.role, user.role_source) == (
        "write",
        "curator",
        "github",
    )
    assert not github_sync.is_stale(user)

    # Access removed on GitHub: the next sync takes the role back.
    github_permission["value"] = "read"
    await github_sync.refresh_github_role(user)
    assert (user.role, user.role_source) == ("viewer", "default")


async def test_a_failed_sync_keeps_the_role_and_retries_later(github_permission):
    from resslab_hub.auth import github_sync

    user = _github_user("write", id="u1", github_role_synced_at=_ago(hours=2))
    roles.apply_role(user)
    github_permission["value"] = RuntimeError("GitHub is down")

    await github_sync.refresh_github_role(user)

    assert (user.github_role, user.role) == ("write", "curator")
    # Not on every request: in a few minutes.
    assert not github_sync.is_stale(user)
    assert github_sync.aware(user.github_role_synced_at) < _ago(minutes=50)


async def test_no_sync_without_the_github_app(github_permission, monkeypatch):
    from resslab_hub.auth import github_sync

    monkeypatch.setattr(github_sync, "configured", lambda: False)
    user = _github_user("write", id="u1")
    await github_sync.refresh_github_role(user)
    assert github_permission["calls"] == 0
    assert user.github_role == "write"


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
    monkeypatch.setattr(mailer.settings, "deployment", None)
    caplog.set_level(logging.WARNING, logger="resslab_hub.auth.mailer")

    await mailer.send_login_mail("ada@example.edu", "123456", "http://x/verify")

    assert "123456" in caplog.text
    assert "http://x/verify" in caplog.text


async def test_a_deployment_without_a_host_refuses_to_send(monkeypatch, caplog):
    """#247: the code went to kubectl logs and the page said "sent"."""
    monkeypatch.setattr(mailer.settings, "smtp_host", None)
    monkeypatch.setattr(mailer.settings, "deployment", "stage")
    caplog.set_level(logging.WARNING, logger="resslab_hub.auth.mailer")

    with pytest.raises(mailer.MailNotConfigured):
        await mailer.send_login_mail("ada@example.edu", "123456", "http://x/verify")

    assert "SMTP_HOST is not set" in caplog.text
    # Nobody can read the log to sign in, so the code has no business there.
    assert "123456" not in caplog.text
    assert "http://x/verify" not in caplog.text


async def test_a_deployment_without_a_host_refuses_a_notice(monkeypatch):
    monkeypatch.setattr(mailer.settings, "smtp_host", "")
    monkeypatch.setattr(mailer.settings, "deployment", "stage")

    with pytest.raises(mailer.MailNotConfigured):
        await mailer.send_notice(
            "boss@epfl.ch", "Subject", "Title", ["Body"], "Go", "http://x/admin", "-"
        )


def test_the_startup_check_says_where_mails_go(monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger="resslab_hub.auth.mailer")
    monkeypatch.setattr(mailer.settings, "smtp_host", None)

    monkeypatch.setattr(mailer.settings, "deployment", "stage")
    mailer.check_at_startup()
    errors = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(errors) == 1
    assert "SMTP_HOST is not set" in errors[0].getMessage()

    caplog.clear()
    monkeypatch.setattr(mailer.settings, "deployment", None)
    mailer.check_at_startup()
    assert [r.levelno for r in caplog.records] == [logging.INFO]
    assert "written to this log" in caplog.text


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

    # The reason is logged, with the relay and the kind of error, so the line
    # in kubectl logs says enough to fix it. The code is never logged.
    assert "relay is down" in caplog.text
    assert "mail.example" in caplog.text
    assert "SMTPConnectError" in caplog.text
    assert "123456" not in caplog.text


def _notice(**changes):
    fields = {
        "email": "boss@epfl.ch",
        "subject": "Ada asks to contribute to RESSLab Hub",
        "title": "A new access request",
        "paragraphs": ["Ada asks for the contributor role."],
        "button": "Open the requests",
        "link": "http://127.0.0.1:5173/admin",
        "footnote": "You are an admin.",
    }
    fields.update(changes)
    return mailer.build_notice(**fields)


def test_a_notice_has_both_parts_and_no_placeholder_left():
    message = _notice()
    text, html = _parts(message)

    assert message["To"] == "boss@epfl.ch"
    for part in (text, html):
        assert "Ada asks for the contributor role." in part
        assert "http://127.0.0.1:5173/admin" in part
        assert "Open the requests" in part
        for name in ("subject", "preheader", "title", "body", "button", "link"):
            assert "{%s}" % name not in part
    assert 'href="http://127.0.0.1:5173/admin"' in html


def test_a_notice_escapes_what_people_typed():
    """A message is user text: it must not become HTML in an admin's mail."""
    message = _notice(
        subject="Mallory\nBcc: everyone@epfl.ch asks",
        paragraphs=["Their message:\n<a href='http://evil'>click</a> {link}"],
    )
    text, html = _parts(message)

    assert "<a href='http://evil'>" not in html
    assert "&lt;a href=" in html
    # The placeholder typed in the message stays text, it is not filled.
    assert "{link}" in html and "{link}" in text
    # No header injection: the line break is folded away.
    assert message["Subject"] == "Mallory Bcc: everyone@epfl.ch asks"
    assert message["Bcc"] is None


async def test_a_notice_is_only_logged_without_a_relay(monkeypatch, caplog):
    monkeypatch.setattr(mailer.settings, "smtp_host", "")
    monkeypatch.setattr(mailer.settings, "deployment", None)
    sent = []

    async def _send(message, **kwargs):
        sent.append(message)

    monkeypatch.setattr(mailer.aiosmtplib, "send", _send)
    with caplog.at_level(logging.INFO):
        await mailer.send_notice(
            "boss@epfl.ch", "Subject", "Title", ["Body"], "Go", "http://x/admin", "-"
        )
    assert sent == []
    assert "http://x/admin" in caplog.text


# --- roles handed out from the Hub ----------------------------------------
def test_grant_raises_a_role(no_config_grants):
    user = User(email="ada@example.com", email_verified_at=object(), role="viewer")
    assert access.grant(user, "contributor")
    assert (user.role, user.role_source, user.role_override) == (
        "contributor",
        "override",
        "contributor",
    )


def test_grant_never_lowers_a_role(no_config_grants):
    curator = _github_user("write")
    assert not access.grant(curator, "contributor")
    assert curator.role_override is None
    assert roles.derive_role(curator) == ("curator", "github")

    # Above what GitHub gives, it does write the decision.
    assert access.grant(curator, "admin")
    assert roles.derive_role(curator) == ("admin", "override")


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
