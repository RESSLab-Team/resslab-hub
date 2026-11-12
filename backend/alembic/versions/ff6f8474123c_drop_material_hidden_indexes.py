"""drop hidden_index and hidden_dataset_index from material

Two old internal indexes of the cyclic coupons. Nobody reads them and
contributors don't know how to fill them, so they leave the data
dictionary too. See RESSLab-Team/resslab-hub#276.

Revision ID: ff6f8474123c
Revises: f5b9d3a7c2e4
Create Date: 2026-11-10 12:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "ff6f8474123c"
down_revision = "f5b9d3a7c2e4"
branch_labels = None
depends_on = None

COLUMNS = ("hidden_index", "hidden_dataset_index")


def upgrade():
    for name in COLUMNS:
        op.drop_column("material", name)


def downgrade():
    # The old values are gone. The columns come back NOT NULL as before, so
    # the rows already in the table get 0, and the default is removed after.
    # The next upload of a CSV that still has the columns writes them again.
    for name in COLUMNS:
        op.add_column(
            "material",
            sa.Column(name, sa.SmallInteger(), nullable=False, server_default="0"),
        )
        op.alter_column("material", name, server_default=None)
