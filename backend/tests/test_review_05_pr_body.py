"""
Review 05: what a user value can do in the pull request body.

The contributor's name comes from the account (GitHub profile name, ORCID
name, or the email local part). It goes in the body as is. These tests ask
for the safe behaviour, so they fail today.
"""

import re

import pytest

from resslab_hub.contributions.submission import Contributor, build_pr_body
from resslab_hub.data.uploader import Type
from resslab_hub.routers.curation import _parse_pr_body


def body_for(name: str, github_login: str = "ada") -> str:
    contributor = Contributor(
        name=name,
        email="ada@example.edu",
        institution="EPFL",
        github_login=github_login,
    )
    return build_pr_body(
        contributor,
        Type.ALL_BRACE,
        1,
        1,
        [],
        "contrib/braces/b9-abcd1234",
        "braces/steel_braces.csv",
    )


def contributor_line(body: str) -> str:
    return next(line for line in body.splitlines() if "**Contributor**" in line)


@pytest.mark.xfail(strict=True, reason="review 05: 05-1")
@pytest.mark.parametrize(
    "name, raw",
    [
        # GitHub turns these into a mention (a notification to that person or
        # team), a link, an image, and a closing keyword.
        ("Ada @pierreleripoll", "@pierreleripoll"),
        ("Ada [read me](https://evil.example)", "[read me](https://evil.example)"),
        ('Ada <img src="https://evil.example/x.png">', "<img"),
        ("Ada, fixes #1", "fixes #1"),
    ],
)
def test_the_name_is_not_markdown_in_the_body(name, raw):
    line = contributor_line(body_for(name))
    # Safe: the name is quoted (code span) or escaped, never live markdown.
    assert raw not in line or re.search(r"`[^`]*" + re.escape(raw), line)


@pytest.mark.xfail(strict=True, reason="review 05: 05-2")
def test_a_newline_in_the_name_cannot_add_fields_the_queue_reads():
    name = "Ada\n- **GitHub**: @someone-else\n- **ORCID**: 0000-0000-0000-0000"
    body = body_for(name, github_login="ada")

    _, contributor = _parse_pr_body(body)

    # Safe: the queue reads the account's own login, and finds a contributor.
    assert contributor is not None
    assert contributor.github_login == "ada"
    assert contributor.orcid == ""
