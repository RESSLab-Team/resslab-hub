"""add invitations and access requests

The two ways an admin hands out a role from the Hub (#248).

Revision ID: b7d2e5f81c3a
Revises: a4e91c73b0d2
Create Date: 2026-10-05 10:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "b7d2e5f81c3a"
down_revision = "a4e91c73b0d2"
branch_labels = None
depends_on = None

ROLES = "('viewer', 'contributor', 'curator', 'admin')"


def upgrade():
    op.create_table(
        "auth_invitation",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("invited_by", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("redeemed_by", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(f"role IN {ROLES}", name="auth_invitation_role_check"),
        sa.ForeignKeyConstraint(["invited_by"], ["auth_user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["redeemed_by"], ["auth_user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "auth_invitation_pending_email",
        "auth_invitation",
        ["email"],
        unique=True,
        postgresql_where=sa.text("redeemed_at IS NULL AND revoked_at IS NULL"),
    )

    op.create_table(
        "auth_access_request",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column(
            "role", sa.String(length=20), nullable=False, server_default="contributor"
        ),
        sa.Column("message", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="pending"
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_by", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(f"role IN {ROLES}", name="auth_access_request_role_check"),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'declined')",
            name="auth_access_request_status_check",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["auth_user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["decided_by"], ["auth_user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_auth_access_request_user_id"),
        "auth_access_request",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "auth_access_request_pending_user",
        "auth_access_request",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade():
    op.drop_index("auth_access_request_pending_user", table_name="auth_access_request")
    op.drop_index(
        op.f("ix_auth_access_request_user_id"), table_name="auth_access_request"
    )
    op.drop_table("auth_access_request")
    op.drop_index("auth_invitation_pending_email", table_name="auth_invitation")
    op.drop_table("auth_invitation")
