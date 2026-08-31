"""add database readme table

Revision ID: b7c1e2d4f5a6
Revises: 2a42de2d3438
Create Date: 2026-08-24 16:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "b7c1e2d4f5a6"
down_revision = "2a42de2d3438"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "database_readme",
        sa.Column("database", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("database"),
    )


def downgrade():
    op.drop_table("database_readme")
