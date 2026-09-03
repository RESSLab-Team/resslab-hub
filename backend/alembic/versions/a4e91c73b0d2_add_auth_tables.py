"""add auth tables

Accounts, identities, sign-ins in progress and sessions (#247).

Revision ID: a4e91c73b0d2
Revises: fd4c75d51fa4
Create Date: 2026-09-03 10:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "a4e91c73b0d2"
down_revision = "fd4c75d51fa4"
branch_labels = None
depends_on = None

ROLES = "('viewer', 'contributor', 'curator', 'admin')"
PROVIDERS = "('email', 'github', 'orcid', 'entra', 'switch')"


def upgrade():
    op.create_table(
        "auth_user",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "display_name", sa.String(length=200), nullable=False, server_default=""
        ),
        sa.Column(
            "institution", sa.String(length=200), nullable=False, server_default=""
        ),
        sa.Column("address", sa.Text(), nullable=False, server_default=""),
        sa.Column("orcid", sa.String(length=50), nullable=False, server_default=""),
        sa.Column(
            "role", sa.String(length=20), nullable=False, server_default="viewer"
        ),
        sa.Column(
            "role_source", sa.String(length=40), nullable=False, server_default="default"
        ),
        sa.Column("role_override", sa.String(length=20), nullable=True),
        sa.Column(
            "github_login", sa.String(length=100), nullable=False, server_default=""
        ),
        sa.Column("github_role", sa.String(length=20), nullable=True),
        sa.Column("github_role_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(f"role IN {ROLES}", name="auth_user_role_check"),
        sa.CheckConstraint(
            f"role_override IS NULL OR role_override IN {ROLES}",
            name="auth_user_role_override_check",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "auth_identity",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("handle", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            f"provider IN {PROVIDERS}", name="auth_identity_provider_check"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["auth_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider", "subject", name="auth_identity_provider_subject"
        ),
    )
    op.create_index(
        op.f("ix_auth_identity_user_id"), "auth_identity", ["user_id"], unique=False
    )

    op.create_table(
        "auth_login_challenge",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False, server_default=""),
        sa.Column("code_hash", sa.String(length=64), nullable=True),
        sa.Column("token_hash", sa.String(length=64), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "redirect_to", sa.String(length=500), nullable=False, server_default="/"
        ),
        sa.Column("link_user_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("ip", sa.String(length=45), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "kind IN ('email', 'oauth_github')",
            name="auth_login_challenge_kind_check",
        ),
        sa.ForeignKeyConstraint(["link_user_id"], ["auth_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_auth_login_challenge_token_hash"),
        "auth_login_challenge",
        ["token_hash"],
        unique=False,
    )

    op.create_table(
        "auth_session",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column(
            "provider", sa.String(length=20), nullable=False, server_default="email"
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip", sa.String(length=45), nullable=False, server_default=""),
        sa.Column("user_agent", sa.String(length=400), nullable=False, server_default=""),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["auth_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        op.f("ix_auth_session_user_id"), "auth_session", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_auth_session_expires_at"), "auth_session", ["expires_at"], unique=False
    )


def downgrade():
    op.drop_index(op.f("ix_auth_session_expires_at"), table_name="auth_session")
    op.drop_index(op.f("ix_auth_session_user_id"), table_name="auth_session")
    op.drop_table("auth_session")
    op.drop_index(
        op.f("ix_auth_login_challenge_token_hash"), table_name="auth_login_challenge"
    )
    op.drop_table("auth_login_challenge")
    op.drop_index(op.f("ix_auth_identity_user_id"), table_name="auth_identity")
    op.drop_table("auth_identity")
    op.drop_table("auth_user")
