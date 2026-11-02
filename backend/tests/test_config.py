"""
The startup check on secrets (#264 C2).

Pure unit tests, no database. DEPLOYMENT is never set in the process: the
tests patch `settings` or call `secret_problems` with explicit values.
"""

import pytest

from resslab_hub.config import refuse_default_secrets, secret_problems, settings

GOOD_API = "a-long-random-api-secret"
GOOD_DB = "db-secret"


@pytest.mark.parametrize("deployment", [None, ""])
@pytest.mark.parametrize("api_password", ["changeit", "", None, "short"])
def test_no_deployment_checks_nothing(deployment, api_password):
    assert secret_problems(deployment, api_password, "") == []


@pytest.mark.parametrize(
    "api_password, expected",
    [
        ("changeit", "API_PASSWORD is the default"),
        ("", "API_PASSWORD is not set"),
        (None, "API_PASSWORD is not set"),
        ("x" * 15, "API_PASSWORD is shorter than 16"),
    ],
)
def test_weak_api_password_is_refused(api_password, expected):
    problems = secret_problems("dev", api_password, GOOD_DB)
    assert len(problems) == 1
    assert expected in problems[0]
    # Never print the secret itself.
    if api_password:
        assert api_password not in problems[0]


def test_sixteen_characters_is_enough():
    assert secret_problems("prod", "x" * 16, GOOD_DB) == []


def test_empty_postgres_password_is_refused():
    problems = secret_problems("stage", GOOD_API, "")
    assert problems == ["POSTGRES_PASSWORD is not set."]


def test_good_secrets_pass():
    assert secret_problems("prod", GOOD_API, GOOD_DB) == []


def test_both_problems_are_reported():
    assert len(secret_problems("prod", "changeit", "")) == 2


def test_refuse_default_secrets_raises_in_a_deployment(monkeypatch):
    monkeypatch.setattr(settings, "deployment", "dev")
    monkeypatch.setattr(settings, "api_password", "changeit")
    monkeypatch.setattr(settings, "postgres_password", GOOD_DB)
    with pytest.raises(RuntimeError, match="DEPLOYMENT=dev: refusing to start"):
        refuse_default_secrets()


def test_refuse_default_secrets_passes_with_good_secrets(monkeypatch):
    monkeypatch.setattr(settings, "deployment", "prod")
    monkeypatch.setattr(settings, "api_password", GOOD_API)
    monkeypatch.setattr(settings, "postgres_password", GOOD_DB)
    refuse_default_secrets()


def test_refuse_default_secrets_ignores_a_laptop(monkeypatch):
    monkeypatch.setattr(settings, "deployment", None)
    monkeypatch.setattr(settings, "api_password", "changeit")
    refuse_default_secrets()
