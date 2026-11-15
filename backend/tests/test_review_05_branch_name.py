"""
Review 05: the branch name and the file paths built from a specimen id.

`_slugify` keeps only `[a-z0-9-]`, so `/`, `..` or `.lock` cannot reach the
branch name. The length is not limited anywhere: not in the id rule, not in
the database column (`String` with no length), not in the slug.
"""

import pytest

from resslab_hub.contributions.submission import SubmissionError, batch_ids
from resslab_hub.data.uploader import Type
from tests.test_contributions import (
    CONTRIBUTOR,
    REPO_CSV,
    FakeClient,
    patch_validation,
    write_archive,
)

# 250 + ".csv" still fits a Linux file name (255 bytes), so the batch can
# be built on disk. The branch segment adds "-" and 8 hex characters: 259.
LONG_ID = "B" * 250
CURVE = "Displacement [mm],Force [kN]\n0,0\n"


@pytest.mark.xfail(strict=True, reason="review 05: 05-4")
def test_a_very_long_id_is_refused_before_github():
    # Safe: refused with a clear message, before any blob is sent to GitHub.
    with pytest.raises(SubmissionError):
        batch_ids(["id", "f_y"], [[LONG_ID, "355"]])


@pytest.mark.xfail(strict=True, reason="review 05: 05-4")
async def test_the_branch_name_has_a_bounded_length(tmp_path, monkeypatch):
    from resslab_hub.contributions.submission import submit_contribution

    patch_validation(monkeypatch)
    client = FakeClient({"braces/steel_braces.csv": REPO_CSV})
    batch = write_archive(
        tmp_path,
        {
            "braces/steel_braces.csv": f"id,f_y,name\n{LONG_ID},400,Long\n",
            f"braces/force_displacement/{LONG_ID}.csv": CURVE,
        },
    )

    result = await submit_contribution(
        str(batch), Type.ALL_BRACE, CONTRIBUTOR, [], client=client
    )

    # A path segment over 255 bytes cannot be a file or a ref on most disks.
    last_segment = result.branch.rsplit("/", 1)[-1]
    assert len(last_segment.encode()) <= 100
