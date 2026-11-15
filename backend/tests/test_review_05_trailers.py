"""
Review 05: who the Hub thinks made a submission.

Provenance is read from the first commit of the pull request that carries a
`Submitted-by` trailer. Any commit counts, not only the ones the Hub's App
made. The data repo is public: anyone can open a pull request from a fork,
with a `contrib/...` branch and any commit message.
"""

import pytest

from resslab_hub.contributions.trailers import (
    build_commit_message,
    owns_submission,
    provenance_from_commits,
)


def forged_commits() -> list:
    """What a fork can push: a commit message that copies the Hub's trailers."""
    return [
        {
            "sha": "fork-sha",
            "message": build_commit_message(
                "data(braces): add 1 experiment (B9)",
                "Real Researcher",
                "real.researcher@example.edu",
                institution="EPFL",
            ),
            "author_name": "Eve",
            "author_email": "eve@example.com",
            "author_date": "2026-11-12T10:00:00Z",
        }
    ]


@pytest.mark.xfail(strict=True, reason="review 05: 05-3")
def test_a_commit_the_hub_did_not_make_gives_no_provenance():
    provenance = provenance_from_commits(forged_commits())

    # Safe: only a commit made by the App counts, so a fork's commit gives
    # nothing, and nobody is shown as the submitter.
    assert provenance is None


@pytest.mark.xfail(strict=True, reason="review 05: 05-3")
def test_the_named_person_does_not_own_a_forged_submission():
    provenance = provenance_from_commits(forged_commits())

    assert not owns_submission(provenance, "real.researcher@example.edu")
