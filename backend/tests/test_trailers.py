"""Provenance carried by commit trailers, and the legacy JSON fallback."""

import json

from resslab_hub.contributions.trailers import (
    build_commit_message,
    owns_submission,
    parse_trailers,
    provenance_from_commits,
    provenance_from_record,
)

TITLE = "data(braces): add 2 experiments (b1…)"


def commit(message: str, date: str = "2026-08-30T16:47:45Z") -> dict:
    return {"sha": "sha", "message": message, "author_date": date}


def test_message_holds_every_field_that_is_set():
    message = build_commit_message(
        TITLE,
        "Ada Lovelace",
        "ada@example.edu",
        institution="EPFL",
        orcid="0000-0001-2345-6789",
        github_login="ada",
        dismissed_warnings=["b1: value far outside the range", "b2: no curve"],
    )
    assert message.splitlines() == [
        TITLE,
        "",
        "Submitted-by: Ada Lovelace <ada@example.edu>",
        "Institution: EPFL",
        "ORCID: 0000-0001-2345-6789",
        "GitHub: @ada",
        "Dismissed-Warning: b1: value far outside the range",
        "Dismissed-Warning: b2: no curve",
    ]


def test_message_leaves_out_what_is_not_known():
    message = build_commit_message(TITLE, "Ada Lovelace", "ada@example.edu")
    assert message == f"{TITLE}\n\nSubmitted-by: Ada Lovelace <ada@example.edu>"


def test_values_are_folded_onto_one_line():
    message = build_commit_message(
        TITLE,
        "Ada\nLovelace <ops@evil.test>",
        "ada@example.edu",
        institution="EPFL\nSTI",
        dismissed_warnings=["two\nlines", "   ", ""],
    )
    trailers = parse_trailers(message)
    assert trailers["Submitted-by"] == ["Ada Lovelace ops@evil.test <ada@example.edu>"]
    assert trailers["Institution"] == ["EPFL STI"]
    # The blank warnings are dropped, not written empty.
    assert trailers["Dismissed-Warning"] == ["two lines"]


def test_parse_ignores_a_prose_last_paragraph():
    assert parse_trailers(f"{TITLE}\n\nSome prose: with a colon.\nAnd more.") == {}


def test_parse_of_an_empty_message():
    assert parse_trailers("") == {}


def test_first_commit_owns_it_and_the_last_says_the_warnings():
    provenance = provenance_from_commits(
        [
            commit(
                build_commit_message(
                    TITLE,
                    "Ada Lovelace",
                    "ada@example.edu",
                    institution="EPFL",
                    orcid="0000-0001",
                    github_login="ada",
                    dismissed_warnings=["first warning"],
                ),
                date="2026-08-30T16:47:45Z",
            ),
            commit(
                build_commit_message(
                    "data(braces): update 2 experiments (b1…)",
                    "Grace Hopper",
                    "grace@example.edu",
                    dismissed_warnings=["second warning"],
                ),
                date="2026-09-01T10:00:00Z",
            ),
        ]
    )
    assert provenance.name == "Ada Lovelace"
    assert provenance.email == "ada@example.edu"
    assert provenance.institution == "EPFL"
    assert provenance.orcid == "0000-0001"
    assert provenance.github_login == "ada"
    assert provenance.submitted_at == "2026-08-30T16:47:45Z"
    assert provenance.dismissed_warnings == ["second warning"]


def test_commits_without_the_trailer_are_not_submissions():
    assert provenance_from_commits([]) is None
    assert provenance_from_commits([commit("fix: a maintainer's own commit")]) is None


def test_a_maintainer_commit_between_two_hub_commits_is_skipped():
    provenance = provenance_from_commits(
        [
            commit(build_commit_message(TITLE, "Ada Lovelace", "ada@example.edu")),
            commit("fix(braces): correct a unit"),
            commit(
                build_commit_message(
                    TITLE,
                    "Ada Lovelace",
                    "ada@example.edu",
                    dismissed_warnings=["still dismissed"],
                )
            ),
        ]
    )
    assert provenance.email == "ada@example.edu"
    assert provenance.dismissed_warnings == ["still dismissed"]


def test_legacy_record_reads_as_the_same_shape():
    provenance = provenance_from_record(
        json.loads(
            json.dumps(
                {
                    "schema": 1,
                    "submitted_at": "2026-08-30T16:47:45+00:00",
                    "contributor": {
                        "name": "Ada Lovelace",
                        "email": "ada@example.edu",
                        "institution": "EPFL",
                        "orcid": "0000-0001",
                        "github_login": "ada",
                        "user_id": "1111",
                    },
                    "dismissed_warnings": ["one warning"],
                }
            )
        )
    )
    assert provenance.name == "Ada Lovelace"
    assert provenance.email == "ada@example.edu"
    assert provenance.institution == "EPFL"
    assert provenance.github_login == "ada"
    assert provenance.submitted_at == "2026-08-30T16:47:45+00:00"
    assert provenance.dismissed_warnings == ["one warning"]


def test_legacy_record_that_is_not_a_record():
    assert provenance_from_record(None) is None
    assert provenance_from_record("not a dict") is None
    assert provenance_from_record({}) == provenance_from_record({"contributor": []})


def test_ownership_is_the_address_whatever_the_case():
    provenance = provenance_from_commits(
        [commit(build_commit_message(TITLE, "Ada Lovelace", "ada@example.edu"))]
    )
    assert owns_submission(provenance, "ADA@Example.edu ")
    assert not owns_submission(provenance, "grace@example.edu")
    assert not owns_submission(provenance, "")
    assert not owns_submission(None, "ada@example.edu")


def test_ownership_by_any_of_the_account_addresses():
    """An account holds several addresses (#402); any one of them owns."""
    provenance = provenance_from_commits(
        [commit(build_commit_message(TITLE, "Ada Lovelace", "ada@example.edu"))]
    )
    assert owns_submission(provenance, ["ada@gmail.com", "Ada@Example.edu"])
    assert owns_submission(provenance, ("ada@example.edu",))
    assert not owns_submission(provenance, ["ada@gmail.com", "grace@example.edu"])
    assert not owns_submission(provenance, [])
