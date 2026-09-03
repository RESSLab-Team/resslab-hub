"""
Handle /auth requests: signing in, signing out, and who am I.

Browsing the databases needs no account. These endpoints exist so that
contributing and curating can (#247): a person proves an address or a provider
account, gets a session cookie, and the contribution pipeline finally knows who
submitted what.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from resslab_hub.auth import email_login, github_oauth, users
from resslab_hub.auth.deps import get_current_user, require_user
from resslab_hub.auth.sessions import (
    LOGIN_COOKIE,
    SESSION_COOKIE,
    clear_login_cookie,
    clear_session_cookie,
    create_session,
    revoke_session,
    set_login_cookie,
    set_session_cookie,
)
from resslab_hub.auth.urls import frontend_url, safe_redirect
from resslab_hub.models.auth import (
    EmailStartRequest,
    EmailStartResponse,
    EmailVerifyRequest,
    IdentityOut,
    MeResponse,
    UserOut,
    VerifyResponse,
)
from resslab_hub.models.database.auth import User
from resslab_hub.utils.database import get_session
from resslab_hub.utils.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


async def _user_out(db: AsyncSession, user: User) -> UserOut:
    identities = await users.list_identities(db, user.id)
    return UserOut(
        id=user.id,
        email=user.email,
        email_verified=user.email_verified_at is not None,
        display_name=user.display_name,
        institution=user.institution,
        orcid=user.orcid,
        role=user.role,
        role_source=user.role_source,
        github_login=user.github_login,
        identities=[
            IdentityOut(id=item.id, provider=item.provider, handle=item.handle)
            for item in identities
        ],
    )


@router.get("/me", response_model=MeResponse)
async def get_me(
    response: Response,
    db: AsyncSession = Depends(get_session),
    user: Optional[User] = Depends(get_current_user),
) -> MeResponse:
    """Who is signed in, if anyone.

    Answers 200 with a null user when nobody is, rather than 401: the SPA calls
    this on every page load, including for visitors who never sign in.
    """
    # Never let the shared response cache (utils/caching.py) or a proxy keep
    # one visitor's answer for the next one.
    response.headers["Cache-Control"] = "no-store"
    if user is None:
        return MeResponse(user=None)
    return MeResponse(user=await _user_out(db, user))


@router.post("/email/start", response_model=EmailStartResponse)
@limiter.limit("10/minute")
async def start_email_login(
    request: Request,
    response: Response,
    payload: EmailStartRequest,
    db: AsyncSession = Depends(get_session),
) -> EmailStartResponse:
    """Mail a sign-in code (and a link that does the same) to an address."""
    ip = request.client.host if request.client else ""
    challenge_id = await email_login.start(
        db, str(payload.email), payload.redirect_to, ip
    )
    if challenge_id is not None:
        set_login_cookie(response, challenge_id)
    # Same answer whether the mail went out, the address was capped, or no
    # account exists: none of that is a stranger's business.
    return EmailStartResponse(sent=True)


@router.post("/email/verify", response_model=VerifyResponse)
@limiter.limit("20/minute")
async def verify_email_login(
    request: Request,
    response: Response,
    payload: EmailVerifyRequest,
    db: AsyncSession = Depends(get_session),
) -> VerifyResponse:
    """Finish a mail sign-in, with the typed code or the mailed link."""
    try:
        if payload.token:
            challenge_id = payload.challenge or request.cookies.get(LOGIN_COOKIE, "")
            if not challenge_id:
                raise email_login.ChallengeError("invalid_or_expired")
            challenge = await email_login.verify_link(db, challenge_id, payload.token)
        else:
            challenge_id = request.cookies.get(LOGIN_COOKIE, "")
            if not challenge_id or not payload.code:
                raise email_login.ChallengeError("invalid_or_expired")
            challenge = await email_login.verify_code(db, challenge_id, payload.code)
    except email_login.ChallengeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=exc.reason
        ) from exc

    user = await users.sign_in_with_email(db, challenge.email)
    token = await create_session(db, user, "email", request)
    redirect_to = safe_redirect(challenge.redirect_to)
    result = VerifyResponse(user=await _user_out(db, user), redirect_to=redirect_to)
    await db.commit()
    set_session_cookie(response, token)
    clear_login_cookie(response)
    response.headers["Cache-Control"] = "no-store"
    return result


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_session),
) -> Response:
    """Sign out. Idempotent, so a stale cookie is not an error."""
    await revoke_session(db, request.cookies.get(SESSION_COOKIE, ""))
    result = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_session_cookie(result)
    return result


@router.get("/identities", response_model=list[IdentityOut])
async def list_identities(
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_user),
) -> list:
    identities = await users.list_identities(db, user.id)
    return [
        IdentityOut(id=item.id, provider=item.provider, handle=item.handle)
        for item in identities
    ]


@router.delete("/identities/{identity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_identity(
    identity_id: str,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_user),
) -> Response:
    """Unlink a provider. The last one cannot go, it would lock the account."""
    identities = await users.list_identities(db, user.id)
    target = next((item for item in identities if item.id == identity_id), None)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No such identity."
        )
    if len(identities) <= 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This is your only way to sign in.",
        )
    if target.provider == "github":
        user.github_login = ""
        user.github_role = None
        user.github_role_synced_at = None
    await db.delete(target)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# GitHub
#
# The same App that opens the contribution pull requests also acts as the
# OAuth client here. Linking it early matters: with a GitHub account attached,
# a contributor is @mentioned on their own pull request, gets GitHub's
# notifications, and can answer a curator's comment in the place the review
# actually happens.
# ---------------------------------------------------------------------------


@router.get("/github/start")
async def start_github_login(
    request: Request,
    redirect_to: str = "/",
    link: bool = False,
    db: AsyncSession = Depends(get_session),
    user: Optional[User] = Depends(get_current_user),
) -> RedirectResponse:
    """Send the browser to GitHub, to sign in or to link an account."""
    if not github_oauth.configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub sign-in is not enabled on this deployment.",
        )
    if link and user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in to continue"
        )
    state = await github_oauth.start(
        db,
        redirect_to=redirect_to,
        link_user_id=user.id if (link and user) else None,
        ip=request.client.host if request.client else "",
    )
    return RedirectResponse(github_oauth.authorize_url(state), status_code=302)


@router.get("/github/callback")
async def finish_github_login(
    request: Request,
    code: str = "",
    state: str = "",
    error: str = "",
    db: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    """Come back from GitHub: sign the person in, or link the account.

    Always answers with a redirect into the SPA, with ``?error=<slug>`` when
    something went wrong, because the browser lands here by navigation and has
    no way to render a JSON error.
    """
    challenge = await github_oauth.consume_state(db, state)
    redirect_to = safe_redirect(challenge.redirect_to) if challenge else "/"
    fallback = "/account" if (challenge and challenge.link_user_id) else "/login"

    if error or not code or challenge is None:
        return _redirect_error(fallback, error or "github_failed")

    try:
        profile = await github_oauth.fetch_profile(code)
    except github_oauth.GitHubOAuthError as exc:
        logger.warning("GitHub sign-in failed: %s", exc)
        return _redirect_error(fallback, "github_failed")

    if challenge.link_user_id:
        user = await users.get_user(db, challenge.link_user_id)
        if user is None:
            return _redirect_error("/login", "github_failed")
        try:
            await users.attach_identity(
                db, user, "github", profile.subject, profile.login
            )
        except users.IdentityTaken:
            return _redirect_error("/account", "identity_taken")
        user.github_login = profile.login
        await db.commit()
        return RedirectResponse(frontend_url(redirect_to), status_code=302)

    try:
        user = await users.sign_in_with_provider(
            db,
            provider="github",
            subject=profile.subject,
            handle=profile.login,
            email=profile.email,
            email_verified=profile.email_verified,
            display_name=profile.name or profile.login,
        )
    except users.EmailTaken:
        # Someone already holds that address. Merging on a matching mail is
        # exactly the takeover we refuse; they sign in with it and link GitHub
        # from the account page instead.
        return _redirect_error("/login", "email_in_use")

    user.github_login = profile.login
    token = await create_session(db, user, "github", request)
    await db.commit()
    response = RedirectResponse(frontend_url(redirect_to), status_code=302)
    set_session_cookie(response, token)
    return response


def _redirect_error(path: str, reason: str) -> RedirectResponse:
    separator = "&" if "?" in path else "?"
    return RedirectResponse(
        frontend_url(f"{path}{separator}error={reason}"), status_code=302
    )
