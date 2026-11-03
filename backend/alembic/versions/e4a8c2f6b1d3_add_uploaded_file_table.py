"""add uploaded file table

Revision ID: e4a8c2f6b1d3
Revises: d3f7a1c9e5b2
Create Date: 2026-11-03 10:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "e4a8c2f6b1d3"
down_revision = "d3f7a1c9e5b2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "uploaded_file",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade():
    op.drop_table("uploaded_file")
