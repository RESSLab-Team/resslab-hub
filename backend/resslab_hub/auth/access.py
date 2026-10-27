"""
Roles handed out from the Hub (#248): invitations and access requests.

Both end the same way as a role change on the admin page: an admin's decision
written to ``User.role_override``. ``grant`` never lowers a role, so approving
a request from someone who is already a curator through GitHub changes nothing.

The mails are best effort. The decision is saved first; a relay that is down
is logged, and the admin page still shows everything.
"""

import logging
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from resslab_hub.auth import mailer, roles
from resslab_hub.auth.challenges import now
from resslab_hub.auth.urls import frontend_url
from resslab_hub.models.database.auth import AccessRequest, Invitation, User

logger = logging.getLogger(__name__)

#: What each role lets someone do, for the mails.
ROLE_WORDS = {
    roles.CONTRIBUTOR: "a contributor: you can submit test data to the databases",
    roles.CURATOR: "a curator: you can review the data people submit",
    roles.ADMIN: "an admin: you can review submissions and decide who can do what",
}


def grant(user: User, role: str) -> bool:
    """Give ``user`` at least ``role``. False when they already had it."""
    current, _ = roles.derive_role(user)
    if roles.rank(role) <= roles.rank(current):
        return False
    user.role_override = role
    roles.apply_role(user)
    return True


def _verified_email(user: User) -> str:
    return (user.email or "") if user.email_verified_at else ""


# --- invitations ------------------------------------------------------------
async def pending_invitation(db: AsyncSession, email: str) -> Optional[Invitation]:
    result = await db.execute(
        select(Invitation).where(
            Invitation.email == email.lower(),
            Invitation.redeemed_at.is_(None),
            Invitation.revoked_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def redeem_invitation(db: AsyncSession, user: User) -> None:
    """At sign-in: the role waiting for this address, if any.

    Only a proven address counts, which is why the invitation needs no secret.
    """
    email = _verified_email(user)
    if not email:
        return
    invitation = await pending_invitation(db, email)
    if invitation is None:
        return
    invitation.redeemed_at = now()
    invitation.redeemed_by = user.id
    grant(user, invitation.role)


async def mail_invitation(invitation: Invitation, inviter: User) -> bool:
    """Tell the person. False when the mail could not be sent."""
    who = inviter.display_name or inviter.email or "An admin"
    try:
        await mailer.send_notice(
            invitation.email,
            subject="You are invited to RESSLab Hub",
            title="You are invited to RESSLab Hub",
            paragraphs=[
                f"{who} invited you to RESSLab Hub as "
                f"{ROLE_WORDS.get(invitation.role, invitation.role)}.",
                "Sign in with this email address to accept. The role is yours "
                "from your first sign-in.",
            ],
            button="Sign in to RESSLab Hub",
            link=frontend_url("/login"),
            footnote="If you did not expect this mail, you can ignore it. "
            "No account is created until you sign in.",
        )
    except mailer.MailError:
        return False
    return True


# --- access requests --------------------------------------------------------
async def latest_request(db: AsyncSession, user_id: str) -> Optional[AccessRequest]:
    result = await db.execute(
        select(AccessRequest)
        .where(AccessRequest.user_id == user_id)
        .order_by(AccessRequest.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def admin_addresses(db: AsyncSession) -> List[str]:
    """Who hears about a new request: the admins, wherever their role is from.

    ``ADMIN_EMAILS`` alone is not enough: most admins come from GitHub.
    """
    result = await db.execute(
        select(User.email).where(
            User.role == roles.ADMIN,
            User.email.is_not(None),
            User.email_verified_at.is_not(None),
            User.disabled_at.is_(None),
        )
    )
    addresses = {email for email in result.scalars().all() if email}
    addresses.update(roles.admin_emails())
    return sorted(addresses)


async def mail_new_request(
    addresses: List[str], user: User, request: AccessRequest
) -> None:
    """Tell the admins. Runs after the response, from what is already loaded."""
    who = user.display_name or user.email or "Someone"
    details = ", ".join(part for part in (user.email, user.institution) if part)
    paragraphs = [f"{who} ({details}) asks for the {request.role} role."]
    if request.message:
        paragraphs.append(f"Their message:\n{request.message}")
    for address in addresses:
        try:
            await mailer.send_notice(
                address,
                subject=f"{who} asks to contribute to RESSLab Hub",
                title="A new access request",
                paragraphs=paragraphs,
                button="Open the requests",
                link=frontend_url("/admin"),
                footnote="You get this mail because you are an admin of RESSLab Hub.",
            )
        except mailer.MailError:
            # Logged by the mailer. The request waits on the admin page.
            continue


async def mail_request_approved(email: str, role: str) -> None:
    """Tell the person their request went through."""
    try:
        await mailer.send_notice(
            email,
            subject="Your RESSLab Hub access request was approved",
            title="Your request was approved",
            paragraphs=[
                f"An admin approved your request. You are now "
                f"{ROLE_WORDS.get(role, role)}.",
            ],
            button="Open RESSLab Hub",
            link=frontend_url("/contribute"),
            footnote="Thank you for sharing your data with the community.",
        )
    except mailer.MailError:
        pass
