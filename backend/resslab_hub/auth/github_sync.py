"""
Keep a user's GitHub permission on the data repository fresh (#248).

That permission makes curators (write or maintain) and admins, so it has to
follow GitHub. It is read when someone signs in or links a GitHub account, and
again on any request once the stored value is an hour old. An hour is
therefore how long someone keeps the role in the Hub after losing their access
on GitHub.

Nothing here commits: the caller does, with the rest of its changes.
"""

import asyncio
import logging
from datetime import timedelta
from typing import Set

from resslab_hub.auth import roles
from resslab_hub.auth.challenges import aware, now
from resslab_hub.contributions.github import DataRepoClient, configured
from resslab_hub.models.database.auth import User

logger = logging.getLogger(__name__)

#: How old the stored permission may get before a request reads it again.
MAX_AGE = timedelta(hours=1)
#: After a failed read, try again this much later, not on every request.
RETRY_AFTER = timedelta(minutes=5)
#: One small GET. A request should not hang on GitHub, so give up early and
#: keep the value we have.
TIMEOUT = 5.0

# Users whose permission is being read right now. The SPA fires several
# requests at once, and one GitHub call is enough for all of them.
_in_flight: Set[str] = set()


def is_stale(user: User) -> bool:
    """True when the user has a GitHub login and its permission is old."""
    if not user.github_login:
        return False
    synced = aware(user.github_role_synced_at)
    return synced is None or now() - synced > MAX_AGE


async def refresh_github_role(user: User) -> None:
    """Read the permission from GitHub, then recompute the role.

    On failure the old permission stays, and the next try is in
    ``RETRY_AFTER``. Without the GitHub App there is nothing to ask, and the
    stored value stays as it is.
    """
    if not user.github_login or not configured() or user.id in _in_flight:
        return
    _in_flight.add(user.id)
    try:
        permission = await asyncio.wait_for(
            DataRepoClient().get_permission(user.github_login), TIMEOUT
        )
    except Exception:
        logger.warning(
            "GitHub permission of @%s could not be read",
            user.github_login,
            exc_info=True,
        )
        user.github_role_synced_at = now() - MAX_AGE + RETRY_AFTER
        return
    finally:
        _in_flight.discard(user.id)
    user.github_role = permission
    user.github_role_synced_at = now()
    roles.apply_role(user)
