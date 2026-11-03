"""
Handle /admin requests: who can do what in the Hub (#248).

Admins only. Three things live here: the members (role and access), the
invitations (a role waiting for an address), and the access requests (someone
signed in asks for the contributor role). An admin can also merge two
accounts of the same person into one (#402).

Every role an admin sets is a ``role_override``. Two kinds of admin are out of
reach: the ones from ``ADMIN_EMAILS`` and the ones from GitHub (admin on the
data repo). Change them there. An admin cannot change their own account
either, so nobody locks themselves out by mistake.
"""

import logging
from typing import Dict, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from resslab_hub.auth import access, roles
from resslab_hub.auth.challenges import now
from resslab_hub.auth.deps import require_contributions_enabled, require_role
from resslab_hub.auth.sessions import revoke_all
from resslab_hub.auth.users import (
    CannotMerge,
    get_by_email,
    get_user,
    merge_users,
    normalize_email,
)
from resslab_hub.models.admin import (
    AccessRequestOut,
    AdminMergeIn,
    AdminUserOut,
    AdminUserPatch,
    InvitationCreated,
    InvitationIn,
    InvitationOut,
)
from resslab_hub.models.database.auth import AccessRequest, Invitation, User
from resslab_hub.utils.database import get_session

logger = logging.getLogger(__name__)

# One instance, so the router and the handlers that need the admin share it
# and FastAPI resolves it once per request.
require_admin = require_role(roles.ADMIN)

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_contributions_enabled), Depends(require_admin)],
)


def _user_out(user: User) -> AdminUserOut:
    return AdminUserOut(
        id=user.id,
        email=user.email,
        email_verified=user.email_verified_at is not None,
        emails=roles.verified_emails(user),
        display_name=user.display_name,
        institution=user.institution,
        role=user.role,
        role_source=user.role_source,
        role_override=user.role_override,
        github_login=user.github_login,
        github_role=user.github_role,
        locked=roles.is_locked_admin(user),
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        disabled=user.disabled_at is not None,
    )


async def _names(db: AsyncSession, ids) -> Dict[str, str]:
    """Display names of the admins who did something, by id."""
    wanted = {item for item in ids if item}
    if not wanted:
        return {}
    result = await db.execute(select(User).where(User.id.in_(wanted)))
    return {user.id: user.display_name or user.email or "" for user in result.scalars()}


# --- members ----------------------------------------------------------------
@router.get("/users", response_model=List[AdminUserOut])
async def list_users(db: AsyncSession = Depends(get_session)) -> list:
    """Everyone with an account, oldest first."""
    result = await db.execute(select(User).order_by(User.created_at))
    return [_user_out(user) for user in result.scalars()]


@router.patch("/users/{user_id}", response_model=AdminUserOut)
async def update_user(
    user_id: str,
    payload: AdminUserPatch,
    db: AsyncSession = Depends(get_session),
    admin: User = Depends(require_admin),
) -> AdminUserOut:
    """Set or clear the role decision, disable or enable the account."""
    target = await get_user(db, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    if target.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="cannot_change_self"
        )
    if roles.is_locked_admin(target):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="locked_admin"
        )

    sent = payload.model_fields_set
    if "role_override" in sent:
        target.role_override = payload.role_override
        roles.apply_role(target)
    if "disabled" in sent and payload.disabled is not None:
        if payload.disabled and target.disabled_at is None:
            target.disabled_at = now()
            await revoke_all(db, target.id)
        elif not payload.disabled:
            target.disabled_at = None
    await db.commit()
    return _user_out(target)


@router.post("/users/{user_id}/merge", response_model=AdminUserOut)
async def merge_user(
    user_id: str,
    payload: AdminMergeIn,
    db: AsyncSession = Depends(get_session),
    admin: User = Depends(require_admin),
) -> AdminUserOut:
    """Fold the account ``from_user_id`` into this one, then delete it.

    For one person with two accounts. Every address and GitHub moves here,
    so the submissions follow (they belong to their addresses). The other
    account's sessions end. An admin can merge another account into their
    own, but not their own account away: that would delete the session in use.
    """
    keep = await get_user(db, user_id)
    other = await get_user(db, payload.from_user_id)
    if keep is None or other is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    if other.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="cannot_change_self"
        )
    try:
        await merge_users(db, keep, other, admin)
    except CannotMerge as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=exc.reason
        ) from exc
    await db.commit()
    logger.info("Admin %s merged account %s into %s", admin.id, other.id, keep.id)
    return _user_out(keep)


# --- invitations ------------------------------------------------------------
def _invitation_status(item: Invitation) -> str:
    if item.redeemed_at is not None:
        return "redeemed"
    if item.revoked_at is not None:
        return "revoked"
    return "pending"


def _invitation_out(item: Invitation, names: Dict[str, str]) -> InvitationOut:
    return InvitationOut(
        id=item.id,
        email=item.email,
        role=item.role,
        status=_invitation_status(item),
        invited_by=names.get(item.invited_by or "", ""),
        created_at=item.created_at,
        redeemed_at=item.redeemed_at,
        revoked_at=item.revoked_at,
    )


@router.get("/invitations", response_model=List[InvitationOut])
async def list_invitations(db: AsyncSession = Depends(get_session)) -> list:
    """Every invitation, newest first. The old ones stay, for the record."""
    result = await db.execute(select(Invitation).order_by(Invitation.created_at.desc()))
    items = list(result.scalars())
    names = await _names(db, (item.invited_by for item in items))
    return [_invitation_out(item, names) for item in items]


@router.post(
    "/invitations",
    response_model=InvitationCreated,
    status_code=status.HTTP_201_CREATED,
)
async def create_invitation(
    payload: InvitationIn,
    db: AsyncSession = Depends(get_session),
    admin: User = Depends(require_admin),
) -> InvitationCreated:
    """Give a role to an address before it has an account, and mail it.

    An address that already has an account is changed in the members list
    instead: there is nothing to wait for.
    """
    email = normalize_email(str(payload.email))
    if await get_by_email(db, email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="already_member"
        )
    if await access.pending_invitation(db, email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="already_invited"
        )
    item = Invitation(email=email, role=payload.role, invited_by=admin.id)
    db.add(item)
    await db.commit()
    # Inline, not in the background: the admin should know when it failed.
    mailed = await access.mail_invitation(item, admin)
    out = _invitation_out(item, {admin.id: admin.display_name or admin.email or ""})
    return InvitationCreated(**out.model_dump(), mailed=mailed)


@router.delete("/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invitation(
    invitation_id: str, db: AsyncSession = Depends(get_session)
) -> Response:
    """Take back an invitation nobody used yet."""
    item = await db.get(Invitation, invitation_id)
    if item is None or _invitation_status(item) != "pending":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    item.revoked_at = now()
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- access requests --------------------------------------------------------
def _request_out(
    item: AccessRequest, user: User, names: Dict[str, str]
) -> AccessRequestOut:
    return AccessRequestOut(
        id=item.id,
        user_id=user.id,
        display_name=user.display_name,
        email=user.email,
        institution=user.institution,
        current_role=user.role,
        role=item.role,
        message=item.message,
        status=item.status,
        created_at=item.created_at,
        decided_by=names.get(item.decided_by or "", ""),
        decided_at=item.decided_at,
    )


@router.get("/access-requests", response_model=List[AccessRequestOut])
async def list_access_requests(db: AsyncSession = Depends(get_session)) -> list:
    """Every request, newest first."""
    result = await db.execute(
        select(AccessRequest, User)
        .join(User, User.id == AccessRequest.user_id)
        .order_by(AccessRequest.created_at.desc())
    )
    rows = list(result.all())
    names = await _names(db, (item.decided_by for item, _ in rows))
    return [_request_out(item, user, names) for item, user in rows]


async def _decide(
    db: AsyncSession, request_id: str, admin: User, approve: bool
) -> tuple:
    row = (
        await db.execute(
            select(AccessRequest, User)
            .join(User, User.id == AccessRequest.user_id)
            .where(AccessRequest.id == request_id)
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    item, user = row
    if item.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="already_decided"
        )
    if approve:
        access.grant(user, item.role)
    item.status = "approved" if approve else "declined"
    item.decided_by = admin.id
    item.decided_at = now()
    await db.commit()
    names = {admin.id: admin.display_name or admin.email or ""}
    return item, user, _request_out(item, user, names)


@router.post("/access-requests/{request_id}/approve", response_model=AccessRequestOut)
async def approve_access_request(
    request_id: str,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
    admin: User = Depends(require_admin),
) -> AccessRequestOut:
    """Give the role asked for, and tell the person."""
    item, user, out = await _decide(db, request_id, admin, approve=True)
    if user.email:
        background.add_task(access.mail_request_approved, user.email, item.role)
    return out


@router.post("/access-requests/{request_id}/decline", response_model=AccessRequestOut)
async def decline_access_request(
    request_id: str,
    db: AsyncSession = Depends(get_session),
    admin: User = Depends(require_admin),
) -> AccessRequestOut:
    """Say no. No mail: the account page shows it, and they may ask again."""
    _, _, out = await _decide(db, request_id, admin, approve=False)
    return out
