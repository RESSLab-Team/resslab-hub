"""Pure-unit tests for the sign-in building blocks (no database)."""

import pytest

from resslab_hub.auth import roles, tokens, urls
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
    user = User(email="boss@epfl.ch", email_verified_at=object(), role_override="viewer")
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
    user = User(email="someone@example.edu", email_verified_at=datetime.now(timezone.utc))
    assert roles.derive_role(user) == ("viewer", "default")


# --- users ----------------------------------------------------------------
def test_email_normalisation():
    assert normalize_email("  Ada@EPFL.CH ") == "ada@epfl.ch"


def test_display_name_guessed_from_the_address():
    assert name_from_email("ada.lovelace@epfl.ch") == "Ada Lovelace"
    assert name_from_email("dlignos@epfl.ch") == "Dlignos"
