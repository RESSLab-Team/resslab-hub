"""
FastAPI dependencies: who is calling, and may they.

Two kinds of caller exist:

* a **person** with a session cookie, which is what the SPA uses;
* a **machine** with the shared HTTP Basic credential (``API_PASSWORD``),
  which is what the data repository's workflows and ``backend/Makefile`` use
  against ``/upload``, ``/validate`` and ``/user``.

The Basic check used to live in ``routers/root.py``; it moved here so both
kinds can be accepted by one dependency. It stays a single shared credential on
purpose: it identifies a job, not a person.
"""

from secrets import compare_digest
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from resslab_hub.auth import github_sync, roles
from resslab_hub.auth.sessions import SESSION_COOKIE, resolve_session
from resslab_hub.config import settings
from resslab_hub.models.database.auth import User
from resslab_hub.utils.database import get_session

# auto_error=False: a request with no Authorization header is not an error
# here, it may be carrying a session cookie instead.
basic_scheme = HTTPBasic(auto_error=False)


def _unauthorized(detail: str, basic: bool = False) -> HTTPException:
    # WWW-Authenticate only when the caller was already speaking Basic:
    # sending it to a browser would pop up the native password dialog on a
    # page that has its own sign-in screen.
    headers = {"WWW-Authenticate": "Basic"} if basic else None
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, headers=headers
    )


def require_contributions_enabled() -> None:
    """404 on the contribution pipeline when ``CONTRIBUTIONS_ENABLED`` is off.

    404 and not 503: 503 already means "no GitHub App" on these routes, while a
    deployment that switched the feature off simply does not have it. Put it
    before any sign-in dependency, so nobody reaches the database.
    """
    if not settings.contributions_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contributions are not enabled on this deployment.",
        )


def check_service_credentials(
    credentials: Optional[HTTPBasicCredentials],
) -> bool:
    """True when the Basic pair matches the configured machine credential."""
    if credentials is None:
        return False
    expected_user: str = str(settings.api_username)
    expected_password: str = str(settings.api_password or "")
    if not expected_password:
        return False
    return compare_digest(credentials.username, expected_user) and compare_digest(
        credentials.password, expected_password
    )


def require_service(
    credentials: Optional[HTTPBasicCredentials] = Depends(basic_scheme),
) -> str:
    """The machine credential, and nothing else (``/upload``, ``/user``)."""
    if not check_service_credentials(credentials):
        raise _unauthorized("Invalid credentials", basic=True)
    return credentials.username  # type: ignore[union-attr]


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> Optional[User]:
    """The signed-in user, or None. Never raises: used by ``GET /auth/me``."""
    token = request.cookies.get(SESSION_COOKIE, "")
    resolved = await resolve_session(db, token)
    if resolved is None:
        return None
    session, user = resolved
    if github_sync.is_stale(user):
        await github_sync.refresh_github_role(user)
        await db.commit()
    # For handlers that take the user off the request rather than through a
    # dependency (the curation ones, called directly by their tests).
    request.state.user = user
    request.state.auth_provider = session.provider
    return user


async def require_user(
    user: Optional[User] = Depends(get_current_user),
) -> User:
    if user is None:
        raise _unauthorized("Sign in to continue")
    return user


def require_role(minimum: str):
    """Dependency factory: signed in, with at least ``minimum``."""

    async def dependency(user: User = Depends(require_user)) -> User:
        if not roles.at_least(user.role, minimum):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action needs the {minimum} role.",
            )
        return user

    return dependency


async def require_user_or_service(
    user: Optional[User] = Depends(get_current_user),
    credentials: Optional[HTTPBasicCredentials] = Depends(basic_scheme),
) -> None:
    """Either a signed-in person or the machine credential.

    ``/validate`` is the endpoint that has both kinds of caller: contributors
    checking a batch in the editor, and the data repository's CI checking a
    pull request.
    """
    if user is not None or check_service_credentials(credentials):
        return
    raise _unauthorized("Sign in to continue", basic=credentials is not None)


def require_role_or_service(minimum: str):
    """``require_role``, but the machine credential also passes."""

    async def dependency(
        user: Optional[User] = Depends(get_current_user),
        credentials: Optional[HTTPBasicCredentials] = Depends(basic_scheme),
    ) -> None:
        if check_service_credentials(credentials):
            return
        if user is None:
            raise _unauthorized("Sign in to continue", basic=credentials is not None)
        if not roles.at_least(user.role, minimum):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action needs the {minimum} role.",
            )

    return dependency
