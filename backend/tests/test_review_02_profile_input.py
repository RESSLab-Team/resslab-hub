# ruff: noqa: F811 (the fixtures are imported from the other test files)
"""
Review 02, questions 7 and 8: the profile, and bad input.

Each test asserts the behaviour we want and is marked xfail(strict): it fails
today and starts to pass when the finding is fixed. See
docs/archive/review/findings/02-identity.md.

The two tests on ``build_pr_body`` need no database.
"""

from urllib.parse import parse_qs, urlsplit

import pytest

from resslab_hub.contributions.submission import (
    Contributor,
    _code_span,
    build_pr_body,
)
from resslab_hub.data.uploader import Type
from resslab_hub.routers.curation import _parse_pr_body
from tests.test_admin import _no_config_grants  # noqa: F401
from tests.test_auth_flow import (  # noqa: F401
    _no_rate_limits,
    _orcid_state,
    github,
    orcid,
)


# --- Q7, the profile (B5) ---------------------------------------------------
@pytest.mark.xfail(strict=True, reason="review 02: 02-10")
async def test_a_person_can_set_their_name_and_institution(client, sign_in):
    """No route writes ``display_name`` or ``institution``. A mail account
    keeps the local part of its address as its name, and ``institution`` is
    always empty, so every submission is signed ``Ada <ada@...>`` only."""
    sign_in(email="ada.l@example.edu", display_name="Ada L", institution="")

    response = await client.patch(
        "/auth/me", json={"display_name": "Ada Lovelace", "institution": "EPFL"}
    )

    assert response.status_code == 200
    me = (await client.get("/auth/me")).json()["user"]
    assert (me["display_name"], me["institution"]) == ("Ada Lovelace", "EPFL")


# --- Q8, bad input (S6) -----------------------------------------------------
@pytest.mark.xfail(strict=True, reason="review 02: 02-11")
async def test_a_long_github_name_does_not_break_the_sign_in(client, github):
    """``display_name`` is String(200). A GitHub name longer than that is
    not cut: today the first sign-in fails on the database (500)."""
    github.name = "A" * 201
    response = await client.get("/auth/github/start")
    state = parse_qs(urlsplit(response.headers["location"]).query)["state"][0]

    callback = await client.get(
        "/auth/github/callback", params={"code": "the-code", "state": state}
    )

    assert callback.status_code == 302
    assert client.cookies.get("resslab_session")


@pytest.mark.xfail(strict=True, reason="review 02: 02-11")
async def test_a_long_orcid_name_does_not_break_the_sign_in(client, orcid):
    """Same for the name on an ORCID record."""
    orcid.name = "A" * 201
    state = await _orcid_state(client)

    callback = await client.get(
        "/auth/orcid/callback", params={"code": "the-code", "state": state}
    )

    assert callback.status_code == 302
    assert client.cookies.get("resslab_session")


@pytest.mark.xfail(strict=True, reason="review 02: 02-12")
@pytest.mark.parametrize(
    "method, path",
    [
        ("patch", "/admin/users/not-a-uuid"),
        ("post", "/admin/users/not-a-uuid/merge"),
        ("delete", "/admin/invitations/not-a-uuid"),
        ("post", "/admin/access-requests/not-a-uuid/approve"),
        ("post", "/admin/access-requests/not-a-uuid/decline"),
    ],
)
async def test_an_id_that_is_not_a_uuid_is_a_404(client, sign_in, method, path):
    """The path ids are plain ``str``. asyncpg refuses them as a UUID and the
    error comes back as a 500."""
    sign_in(email="me@example.org", role="admin", role_override="admin")
    me = (await client.get("/auth/me")).json()["user"]
    body = {"from_user_id": me["id"]} if path.endswith("/merge") else {}
    kwargs = {} if method == "delete" else {"json": body}

    response = await getattr(client, method)(path, **kwargs)

    assert response.status_code == 404


def _pr_body(name):
    return build_pr_body(
        Contributor(name=name, email="eve@example.org"),
        Type.ALL_BRACE,
        experiment_count=1,
        curve_count=0,
        dismissed_warnings=[],
    )


@pytest.mark.xfail(strict=True, reason="review 02: 02-13")
def test_the_name_in_the_pull_request_is_plain_text():
    """The name comes from GitHub or ORCID and nobody can change it. In the
    pull request body it is Markdown: an @mention pings that user, a link is
    a link. The dismissed warnings already go through ``_code_span``."""
    name = "Eve @victim [docs](https://evil.example)"

    body = _pr_body(name)

    assert "@victim" not in body.replace(_code_span(name), "")


@pytest.mark.xfail(strict=True, reason="review 02: 02-13")
def test_a_name_cannot_add_a_line_the_review_page_reads():
    """A line break in the name writes a ``- **ORCID**:`` line in the body,
    and ``_parse_pr_body`` (the review page) shows it as the contributor's
    iD. The account has no ORCID at all."""
    body = _pr_body("Eve (x)\n- **ORCID**: 0000-0002-1825-0097\nEve")

    _, contributor = _parse_pr_body(body)

    assert contributor is not None
    assert contributor.orcid == ""
