"""
Accounts, identities and sessions for the contribution pipeline (#247).

Hand-written tables, like ``dictionary.py``. Nothing here comes from a data
dictionary, so ``generate_model.py`` never touches this module.

Shape (epic #255): one ``User`` row per person, one ``Identity`` row per way
they can prove who they are. Identities are linked only by an explicit flow
while signed in, never merged automatically because two providers report the
same address. ``LoginChallenge`` is the short-lived state of a sign-in in
progress (the mailed code, or the OAuth ``state``), ``Session`` is a signed-in
browser. ``Invitation`` and ``AccessRequest`` are the two ways an admin hands
out a role from the Hub (#248).

Enum-like columns are ``String`` + ``CheckConstraint`` rather than Postgres
enums: adding a role or a provider then costs an ordinary migration instead of
an ``ALTER TYPE``. Emails are stored lower-cased with a plain unique index, so
no ``citext`` extension is needed in the throwaway worktree and test databases.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID

from resslab_hub.utils.database import Base

#: Roles, weakest first. ``resslab_hub.auth.roles`` compares by this order.
ROLE_ORDER = ("viewer", "contributor", "curator", "admin")

#: Ways an identity can be proven. ``orcid``, ``entra`` and ``switch`` are
#: reserved for the later provider issues (#249, #250, #252).
PROVIDERS = ("email", "github", "orcid", "entra", "switch")

#: Kinds of sign-in in progress.
CHALLENGE_KINDS = ("email", "oauth_github")

#: Where an access request is.
REQUEST_STATUSES = ("pending", "approved", "declined")


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):  # type: ignore
    """One person. Everything they can sign in with hangs off ``Identity``."""

    __tablename__ = "auth_user"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    #: Lower-cased. Nullable because a GitHub-only account may have no
    #: address we are allowed to see; contributing requires a verified one.
    email = Column(String(320), unique=True, nullable=True)
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    display_name = Column(String(200), nullable=False, server_default="")
    institution = Column(String(200), nullable=False, server_default="")
    #: Free-text postal address, optional, for the lab's records.
    address = Column(Text, nullable=False, server_default="")
    orcid = Column(String(50), nullable=False, server_default="")
    #: Effective role, recomputed by ``auth.roles.apply_role``.
    role = Column(String(20), nullable=False, server_default="viewer")
    #: Why ``role`` has that value: ``admin-email``, ``github``,
    #: ``override``, ``academic-email`` or ``default``.
    role_source = Column(String(40), nullable=False, server_default="default")
    #: Set by an admin; wins over everything derived, in both directions,
    #: except an admin from ``ADMIN_EMAILS`` or from GitHub (#248).
    role_override = Column(String(20), nullable=True)
    #: Mirror of the linked GitHub identity, kept here so the permission on the
    #: data repo can be refreshed and read without joining.
    github_login = Column(String(100), nullable=False, server_default="")
    #: GitHub's permission on the data repo: ``admin``, ``write``, ``read`` or
    #: ``none``. Read again by ``auth.github_sync`` once an hour old.
    github_role = Column(String(20), nullable=True)
    github_role_synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    #: Set by an admin to lock the account out.
    disabled_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "role IN ('viewer', 'contributor', 'curator', 'admin')",
            name="auth_user_role_check",
        ),
        CheckConstraint(
            "role_override IS NULL OR role_override IN "
            "('viewer', 'contributor', 'curator', 'admin')",
            name="auth_user_role_override_check",
        ),
    )


class Identity(Base):  # type: ignore
    """One way a user proves who they are."""

    __tablename__ = "auth_identity"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(
        UUID(as_uuid=False),
        ForeignKey("auth_user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider = Column(String(20), nullable=False)
    #: The provider's immutable id for this person: the address for ``email``,
    #: the numeric account id for ``github`` (logins get renamed, ids don't).
    subject = Column(String(255), nullable=False)
    #: Display form of the subject: the address, the GitHub login.
    handle = Column(String(255), nullable=False, server_default="")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("provider", "subject", name="auth_identity_provider_subject"),
        CheckConstraint(
            "provider IN ('email', 'github', 'orcid', 'entra', 'switch')",
            name="auth_identity_provider_check",
        ),
    )


class LoginChallenge(Base):  # type: ignore
    """A sign-in in progress: a mailed code, or an OAuth round trip.

    Only hashes of the code and of the link token are stored, so a database
    dump does not let anyone finish someone else's sign-in.
    """

    __tablename__ = "auth_login_challenge"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    kind = Column(String(20), nullable=False)
    #: Set for ``email`` challenges (lower-cased), empty for OAuth ones.
    email = Column(String(320), nullable=False, server_default="")
    code_hash = Column(String(64), nullable=True)
    token_hash = Column(String(64), nullable=True, index=True)
    attempts = Column(Integer, nullable=False, server_default="0")
    #: Where to send the browser afterwards; a path, validated on write.
    redirect_to = Column(String(500), nullable=False, server_default="/")
    #: Set when the flow was started from an account page to add a provider to
    #: an existing user, instead of signing in.
    link_user_id = Column(
        UUID(as_uuid=False),
        ForeignKey("auth_user.id", ondelete="CASCADE"),
        nullable=True,
    )
    ip = Column(String(45), nullable=False, server_default="")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "kind IN ('email', 'oauth_github')",
            name="auth_login_challenge_kind_check",
        ),
    )


class Session(Base):  # type: ignore
    """A signed-in browser. Server side, so an admin can revoke it."""

    __tablename__ = "auth_session"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    #: sha256 of the cookie value. The value itself is never stored.
    token_hash = Column(String(64), nullable=False, unique=True)
    user_id = Column(
        UUID(as_uuid=False),
        ForeignKey("auth_user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    #: Which provider this browser signed in with.
    provider = Column(String(20), nullable=False, server_default="email")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    ip = Column(String(45), nullable=False, server_default="")
    user_agent = Column(String(400), nullable=False, server_default="")
    revoked_at = Column(DateTime(timezone=True), nullable=True)


class Invitation(Base):  # type: ignore
    """A role waiting for an address that has no account yet.

    Redeemed at the first sign-in that proves the address. The address is the
    proof, so the invitation carries no secret.
    """

    __tablename__ = "auth_invitation"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    #: Lower-cased, like ``User.email``.
    email = Column(String(320), nullable=False)
    role = Column(String(20), nullable=False)
    invited_by = Column(
        UUID(as_uuid=False),
        ForeignKey("auth_user.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    redeemed_at = Column(DateTime(timezone=True), nullable=True)
    redeemed_by = Column(
        UUID(as_uuid=False),
        ForeignKey("auth_user.id", ondelete="SET NULL"),
        nullable=True,
    )
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "role IN ('viewer', 'contributor', 'curator', 'admin')",
            name="auth_invitation_role_check",
        ),
        # One open invitation per address. Old ones stay, for the record.
        Index(
            "auth_invitation_pending_email",
            "email",
            unique=True,
            postgresql_where=text("redeemed_at IS NULL AND revoked_at IS NULL"),
        ),
    )


class AccessRequest(Base):  # type: ignore
    """Someone signed in asks an admin for a role (today, contributor)."""

    __tablename__ = "auth_access_request"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(
        UUID(as_uuid=False),
        ForeignKey("auth_user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(20), nullable=False, server_default="contributor")
    #: Who they are and what they want to submit, in their own words.
    message = Column(Text, nullable=False, server_default="")
    status = Column(String(20), nullable=False, server_default="pending")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    decided_by = Column(
        UUID(as_uuid=False),
        ForeignKey("auth_user.id", ondelete="SET NULL"),
        nullable=True,
    )
    decided_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "role IN ('viewer', 'contributor', 'curator', 'admin')",
            name="auth_access_request_role_check",
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'declined')",
            name="auth_access_request_status_check",
        ),
        # One open request per person.
        Index(
            "auth_access_request_pending_user",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
    )
