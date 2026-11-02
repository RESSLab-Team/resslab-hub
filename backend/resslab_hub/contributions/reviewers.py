"""
Ask the data curators to review each pull request the Hub opens (#266).

GitHub only notifies people who watch the repo or who are requested as
reviewers. Without a request, a submission waits and nobody knows.

Who is asked comes from `DATA_REPO_REVIEWERS`. The default, ``admins``, is
every account with admin on the data repo, read from GitHub at each pull
request. That is the same permission `auth/roles.py` turns into the Hub's
admin role (`GITHUB_ROLES`), so the reviewers and the Hub admins are one set:
to add a reviewer, make them admin on the data repo.

This is best effort. The pull request is already open when it runs, so a
failure is logged and the submit still succeeds.
"""

import asyncio
import logging
from typing import List, Optional

from resslab_hub.config import settings
from resslab_hub.contributions.github import DataRepoClient, describe_error

logger = logging.getLogger(__name__)

#: Two small calls. The contributor is waiting for the submit to answer.
TIMEOUT = 10.0


def configured_reviewers() -> Optional[List[str]]:
    """The fixed list from the setting, or None to ask GitHub for the admins."""
    raw = str(settings.data_repo_reviewers or "").strip()
    if raw.lower() in ("", "admins"):
        return None
    if raw.lower() == "none":
        return []
    return [login.strip() for login in raw.split(",") if login.strip()]


async def _request(client: DataRepoClient, number: int, opened_by: str) -> List[str]:
    logins = configured_reviewers()
    if logins is None:
        logins = await client.list_admin_logins()
    # Nobody reviews their own pull request: GitHub would refuse the request.
    logins = [login for login in logins if login.lower() != opened_by.lower()]
    await client.request_reviewers(number, logins)
    return logins


async def request_reviews(
    client: DataRepoClient, number: int, opened_by: str = ""
) -> List[str]:
    """Request the reviewers on pull request `number`. Never raises.

    `opened_by` is the GitHub login of the person behind the pull request
    (the contributor, or the curator of a verification), left out of the
    request. Returns the logins asked, empty when nothing was requested.
    """
    try:
        logins = await asyncio.wait_for(
            _request(client, number, opened_by or ""), TIMEOUT
        )
    except Exception as exc:
        logger.warning(
            "Reviewers not requested on #%s: %s",
            number,
            describe_error(exc) or type(exc).__name__,
        )
        return []
    if logins:
        logger.info("Reviewers requested on #%s: %s", number, ", ".join(logins))
    return logins
