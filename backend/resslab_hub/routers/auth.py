"""
Handle /auth requests: signing in, signing out, and who am I.

Browsing the databases needs no account. These endpoints exist so that
contributing and curating can (#247): a person proves an address or a provider
account, gets a session cookie, and the contribution pipeline knows who
submitted what.
"""

import logging
from typing import Optional
from urllib.parse import urlencode

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from resslab_hub.auth import (
    access,
    email_login,
    github_oauth,
    github_sync,
    mailer,
    orcid_oauth,
    roles,
    users,
)
from resslab_hub.auth.deps import (
    get_current_user,
    require_contributions_enabled,
    require_user,
)
from resslab_hub.auth.sessions import (
    LOGIN_COOKIE,
    SESSION_COOKIE,
    clear_login_cookie,
    clear_session_cookie,
    client_ip,
    create_session,
    revoke_session,
    set_login_cookie,
    set_session_cookie,
)
from resslab_hub.auth.urls import frontend_url, safe_redirect
from resslab_hub.models.auth import (
    AccessRequestIn,
    AccessRequestStatus,
    AddEmailRequest,
    AddEmailVerifyRequest,
    EmailStartRequest,
    EmailStartResponse,
    EmailVerifyRequest,
    IdentityOut,
    MeResponse,
    UserOut,
    VerifyResponse,
)
from resslab_hub.models.database.auth import AccessRequest, User
from resslab_hub.utils.database import get_session
from resslab_hub.utils.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# Signing in only serves the contribution pipeline, so it goes off with it
# (CONTRIBUTIONS_ENABLED). On each route and not on the router: `GET /me`
# stays, the sidebar asks it on every page and must keep hearing "nobody".
_ENABLED = [Depends(require_contributions_enabled)]


def _request_status(item: Optional[AccessRequest]) -> Optional[AccessRequestStatus]:
    if item is None:
        return None
    return AccessRequestStatus(
        status=item.status,
        role=item.role,
        created_at=item.created_at,
        decided_at=item.decided_at,
    )


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
        access_request=_request_status(await access.latest_request(db, user.id)),
    )


@router.get("/me", response_model=MeResponse)
async def get_me(
    response: Response,
    db: AsyncSession = Depends(get_session),
    user: Optional[User] = Depends(get_current_user),
) -> MeResponse:
    """Who is signed in, if anyone.

    200 with a null user when nobody is, rather than 401: the SPA asks on
    every page load, and an anonymous visitor is not an error.
    """
    # Never let the shared response cache or a proxy keep one visitor's
    # answer for the next one.
    response.headers["Cache-Control"] = "no-store"
    if user is None:
        return MeResponse(user=None)
    return MeResponse(user=await _user_out(db, user))


@router.post("/email/start", response_model=EmailStartResponse, dependencies=_ENABLED)
@limiter.limit("10/minute")
async def start_email_login(
    request: Request,
    response: Response,
    payload: EmailStartRequest,
    db: AsyncSession = Depends(get_session),
) -> EmailStartResponse:
    """Mail a sign-in code (and a link that does the same) to an address."""
    try:
        challenge_id = await email_login.start(
            db, str(payload.email), payload.redirect_to, client_ip(request)
        )
    except mailer.MailNotConfigured as exc:
        # A deployment with no relay. Not worth a retry, so not "mail_failed":
        # the page says email sign-in is not set up here.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="mail_not_configured",
        ) from exc
    except mailer.MailError as exc:
        # The only case where the answer is not the same for everyone. It says
        # nothing about the address, only that our relay is down, and the
        # person needs to know no mail is coming.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="mail_failed"
        ) from exc
    if challenge_id is not None:
        set_login_cookie(response, challenge_id)
    # Same answer whether the mail went out or the address was capped.
    return EmailStartResponse(sent=True)


@router.post("/email/verify", response_model=VerifyResponse, dependencies=_ENABLED)
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
    if user.disabled_at is not None:
        # The code was right, so saying it costs nothing: only the owner of
        # the address gets this far.
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="account_disabled"
        )
    # A linked GitHub account may have gained or lost access to the data repo.
    await github_sync.refresh_github_role(user)
    token = await create_session(db, user, "email", request)
    redirect_to = safe_redirect(challenge.redirect_to)
    result = VerifyResponse(user=await _user_out(db, user), redirect_to=redirect_to)
    await db.commit()
    set_session_cookie(response, token)
    clear_login_cookie(response)
    response.headers["Cache-Control"] = "no-store"
    return result


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, dependencies=_ENABLED)
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> Response:
    """Sign out. Idempotent, so a stale cookie is not an error."""
    await revoke_session(db, request.cookies.get(SESSION_COOKIE, ""))
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_session_cookie(response)
    return response


@router.get("/identities", response_model=list[IdentityOut], dependencies=_ENABLED)
async def list_identities(
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_user),
) -> list:
    identities = await users.list_identities(db, user.id)
    return [
        IdentityOut(id=item.id, provider=item.provider, handle=item.handle)
        for item in identities
    ]


@router.delete(
    "/identities/{identity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=_ENABLED,
)
async def delete_identity(
    identity_id: str,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_user),
) -> Response:
    """Unlink a provider, or remove an added address (#402).

    Not the last identity, it would lock the account. And not the main
    address: it signs new submissions and gets the mails, so the person picks
    another main address first. Once removed, an address no longer finds the
    account, and the role is worked out again without it.
    """
    try:
        await users.remove_identity(db, user, identity_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="not_found"
        ) from exc
    except users.CannotUnlink as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="cannot_unlink"
        ) from exc
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/identities/{identity_id}/main",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=_ENABLED,
)
async def set_main_email(
    identity_id: str,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_user),
) -> Response:
    """Make one of the account's addresses the main one (#402).

    The main address signs new submissions and gets the mails.
    """
    try:
        await users.set_main_email(db, user, identity_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="not_found"
        ) from exc
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/emails", response_model=EmailStartResponse, dependencies=_ENABLED)
@limiter.limit("10/minute")
async def start_add_email(
    request: Request,
    response: Response,
    payload: AddEmailRequest,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_user),
) -> EmailStartResponse:
    """Mail a code to an address the signed-in person wants to add (#402).

    Whether another account holds the address is only said at the code step,
    to whoever proved they read its mailbox.
    """
    email = users.normalize_email(str(payload.email))
    if email in roles.verified_emails(user):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="already_yours"
        )
    try:
        challenge_id = await email_login.start(
            db,
            email,
            redirect_to="/account",
            ip=client_ip(request),
            link_user_id=user.id,
        )
    except mailer.MailNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="mail_not_configured",
        ) from exc
    except mailer.MailError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="mail_failed"
        ) from exc
    if challenge_id is not None:
        set_login_cookie(response, challenge_id)
    return EmailStartResponse(sent=True)


@router.post("/emails/verify", response_model=UserOut, dependencies=_ENABLED)
@limiter.limit("20/minute")
async def verify_add_email(
    request: Request,
    response: Response,
    payload: AddEmailVerifyRequest,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_user),
) -> UserOut:
    """Add the address, with the code typed in the session that asked (#402).

    No session is created: this browser is already signed in, as the account
    the address goes to. An address of another account is refused, with one
    exception. When this account is bare (only an ORCID iD or a GitHub login,
    no address, see ``users.is_bare``), the person just proved both the
    identity and the mailbox. Its identity then moves to the account holding
    the address, and this browser is signed in there instead (#250).
    """
    challenge_id = request.cookies.get(LOGIN_COOKIE, "")
    try:
        if not challenge_id:
            raise email_login.ChallengeError("invalid_or_expired")
        challenge = await email_login.verify_code(
            db, challenge_id, payload.code, link_user_id=user.id
        )
    except email_login.ChallengeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=exc.reason
        ) from exc
    # Read before add_email: after its rollback, ``user`` is expired.
    email, user_id, bare = challenge.email, user.id, users.is_bare(user)
    try:
        await users.add_email(db, user, email)
    except users.EmailTaken as exc:
        # The code was right, so only the owner of the mailbox learns this.
        # Keep the challenge spent, so it cannot be tried again.
        joined = await _join_bare_account(db, user_id, email) if bare else None
        if isinstance(joined, User):
            token = await create_session(db, joined, "email", request)
            result = await _user_out(db, joined)
            await db.commit()
            set_session_cookie(response, token)
            clear_login_cookie(response)
            response.headers["Cache-Control"] = "no-store"
            return result
        await db.commit()
        if joined == "account_disabled":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="account_disabled"
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="email_in_use"
        ) from exc
    result = await _user_out(db, user)
    await db.commit()
    clear_login_cookie(response)
    response.headers["Cache-Control"] = "no-store"
    return result


async def _join_bare_account(db: AsyncSession, bare_id: str, email: str):
    """Move a bare account into the holder of ``email``.

    The holder, or the reason it did not work (``account_disabled``, or
    another refusal of ``users.absorb_bare_account``).
    """
    bare = await users.get_user(db, bare_id)
    holder = await users.get_by_email(db, email)
    if bare is None or holder is None:
        return "email_in_use"
    try:
        await users.absorb_bare_account(db, holder, bare)
    except users.CannotAbsorb as exc:
        return exc.reason
    await github_sync.refresh_github_role(holder)
    return holder


@router.post(
    "/access-request",
    response_model=AccessRequestStatus,
    status_code=status.HTTP_201_CREATED,
    dependencies=_ENABLED,
)
@limiter.limit("5/hour")
async def request_access(
    request: Request,
    response: Response,
    payload: AccessRequestIn,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_user),
) -> AccessRequestStatus:
    """Ask the admins for the contributor role (#248).

    For someone whose address is not academic, so it did not grant the role.
    One open request at a time; after a decline they may ask again.
    """
    if not user.email or user.email_verified_at is None:
        # A submission is signed with the address, so the role is useless
        # without one.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="email_required"
        )
    if roles.at_least(user.role, roles.CONTRIBUTOR):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="already_granted"
        )
    previous = await access.latest_request(db, user.id)
    if previous is not None and previous.status == "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="already_pending"
        )
    item = AccessRequest(
        user_id=user.id,
        role=roles.CONTRIBUTOR,
        message=payload.message.strip(),
        status="pending",
    )
    db.add(item)
    try:
        await db.commit()
    except IntegrityError as exc:
        # Two tabs at once: the unique index keeps one pending request.
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="already_pending"
        ) from exc
    addresses = await access.admin_addresses(db)
    background.add_task(access.mail_new_request, addresses, user, item)
    return _request_status(item)


# --- GitHub ---------------------------------------------------------------


@router.get("/github/start", dependencies=_ENABLED)
async def start_github_login(
    request: Request,
    redirect_to: str = "/",
    link: bool = False,
    db: AsyncSession = Depends(get_session),
    user: Optional[User] = Depends(get_current_user),
) -> RedirectResponse:
    """Send the browser to GitHub, to sign in or to link an account."""
    if not github_oauth.configured():
        # The button is always offered, so people do land here on a
        # deployment without the OAuth pair. This is a navigation, not a
        # fetch: a JSON error would be shown raw in the tab. Go back to the
        # login page with a reason instead, like the callback does.
        return RedirectResponse(
            frontend_url("/login?error=github_disabled"), status_code=302
        )
    if link and user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in to continue"
        )
    state = await github_oauth.start(
        db,
        redirect_to=redirect_to,
        link_user_id=user.id if (link and user) else None,
        ip=client_ip(request),
    )
    response = RedirectResponse(github_oauth.authorize_url(state), status_code=302)
    # The callback must come back to this browser: see consume_state.
    set_login_cookie(response, state)
    return response


@router.get("/github/callback", dependencies=_ENABLED)
async def finish_github_login(
    request: Request,
    code: str = "",
    state: str = "",
    error: str = "",
    db: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    """Come back from GitHub: sign the person in, or link the account.

    Always a redirect into the SPA, with ``?error=<slug>`` when something went
    wrong: the browser lands here by navigation and cannot render JSON.
    """
    challenge = await github_oauth.consume_state(
        db, state, request.cookies.get(LOGIN_COOKIE, "")
    )
    redirect_to = safe_redirect(challenge.redirect_to) if challenge else "/"
    fallback = "/account" if (challenge and challenge.link_user_id) else "/login"

    if challenge is None:
        return _redirect_error(fallback, "github_failed")
    if error:
        # GitHub's own slugs are not ours to echo: the person either said no
        # or something broke.
        return _redirect_error(
            fallback, "github_denied" if error == "access_denied" else "github_failed"
        )
    if not code:
        return _redirect_error(fallback, "github_failed")

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
        # Write access on the data repo makes a curator: no need to wait for
        # the next sign-in to get it.
        await github_sync.refresh_github_role(user)
        await db.commit()
        return _redirect(redirect_to)

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
        # the takeover we refuse; they sign in with it and link GitHub from
        # the account page instead.
        return _redirect_error("/login", "email_in_use")
    if user.disabled_at is not None:
        await db.commit()
        return _redirect_error("/login", "account_disabled")

    user.github_login = profile.login
    await github_sync.refresh_github_role(user)
    token = await create_session(db, user, "github", request)
    await db.commit()
    response = _redirect(redirect_to)
    set_session_cookie(response, token)
    return response


# --- ORCID (#250) -----------------------------------------------------------


@router.get("/orcid/start", dependencies=_ENABLED)
async def start_orcid_login(
    request: Request,
    redirect_to: str = "/",
    link: bool = False,
    db: AsyncSession = Depends(get_session),
    user: Optional[User] = Depends(get_current_user),
) -> RedirectResponse:
    """Send the browser to ORCID, to sign in or to link an iD."""
    if not orcid_oauth.configured():
        # Same as GitHub: the button is always there, the click comes back.
        return RedirectResponse(
            frontend_url("/login?error=orcid_disabled"), status_code=302
        )
    if link and user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in to continue"
        )
    state = await orcid_oauth.start(
        db,
        redirect_to=redirect_to,
        link_user_id=user.id if (link and user) else None,
        ip=client_ip(request),
    )
    response = RedirectResponse(orcid_oauth.authorize_url(state), status_code=302)
    set_login_cookie(response, state)
    return response


@router.get("/orcid/callback", dependencies=_ENABLED)
async def finish_orcid_login(
    request: Request,
    code: str = "",
    state: str = "",
    error: str = "",
    db: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    """Come back from ORCID: sign the person in, or link the iD.

    ORCID gives no address (we do not ask for it). A first sign-in makes an
    account with only the iD and sends the person to the account page to add
    an address, once. If that address belongs to an existing account, the
    two join there (``verify_add_email``).
    """
    challenge = await orcid_oauth.consume_state(
        db, state, request.cookies.get(LOGIN_COOKIE, "")
    )
    redirect_to = safe_redirect(challenge.redirect_to) if challenge else "/"
    fallback = "/account" if (challenge and challenge.link_user_id) else "/login"

    if challenge is None:
        return _redirect_error(fallback, "orcid_failed")
    if error:
        return _redirect_error(
            fallback, "orcid_denied" if error == "access_denied" else "orcid_failed"
        )
    if not code:
        return _redirect_error(fallback, "orcid_failed")

    try:
        profile = await orcid_oauth.fetch_profile(code)
    except orcid_oauth.OrcidOAuthError as exc:
        logger.warning("ORCID sign-in failed: %s", exc)
        return _redirect_error(fallback, "orcid_failed")

    if challenge.link_user_id:
        user = await users.get_user(db, challenge.link_user_id)
        if user is None:
            return _redirect_error("/login", "orcid_failed")
        try:
            await users.attach_identity(
                db, user, "orcid", profile.subject, profile.subject
            )
        except users.IdentityTaken:
            # The iD sits on another account. When that one is bare (the
            # person signed in with ORCID once and skipped the address), it
            # joins this one: the person proved both. Else, refused.
            identity = await users.get_identity(db, "orcid", profile.subject)
            holder = await users.get_user(db, identity.user_id) if identity else None
            try:
                if holder is None:
                    raise users.CannotAbsorb("not_bare")
                await users.absorb_bare_account(db, user, holder)
            except users.CannotAbsorb:
                return _redirect_error("/account", "identity_taken")
        # A proved iD wins over a typed one.
        user.orcid = profile.subject
        await db.commit()
        return _redirect(redirect_to)

    known = await users.get_identity(db, "orcid", profile.subject) is not None
    user = await users.sign_in_with_provider(
        db,
        provider="orcid",
        subject=profile.subject,
        handle=profile.subject,
        display_name=profile.name or profile.subject,
    )
    if user.disabled_at is not None:
        await db.commit()
        return _redirect_error("/login", "account_disabled")

    user.orcid = profile.subject
    await github_sync.refresh_github_role(user)
    token = await create_session(db, user, "orcid", request)
    await db.commit()
    if not known and not user.email:
        # First time, no address: ask for one, then go on where they were.
        redirect_to = "/account?" + urlencode({"add_email": "1", "next": redirect_to})
    response = _redirect(redirect_to)
    set_session_cookie(response, token)
    return response


def _redirect(path: str) -> RedirectResponse:
    response = RedirectResponse(frontend_url(path), status_code=302)
    clear_login_cookie(response)
    return response


def _redirect_error(path: str, reason: str) -> RedirectResponse:
    separator = "&" if "?" in path else "?"
    return _redirect(f"{path}{separator}{urlencode({'error': reason})}")
