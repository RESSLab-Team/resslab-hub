"""add group to dictionary columns

Revision ID: fd4c75d51fa4
Revises: c3f7a91b2e08
Create Date: 2026-09-01 16:05:58.355628

The scientific category of each variable, from the `group` column the data
dictionaries carry since RESSLab-Team/resslab-hub-data#46. The empty server
default keeps the old rows and any dictionary without the column valid.

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "fd4c75d51fa4"
down_revision = "c3f7a91b2e08"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "dictionary_column",
        sa.Column("group", sa.String(), server_default="", nullable=False),
    )


def downgrade():
    op.drop_column("dictionary_column", "group")
