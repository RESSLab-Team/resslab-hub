"""rename uvc_e to gpa, drop material file, fix residual stress fy_e type

Revision ID: c3f7a91b2e08
Revises: b7c1e2d4f5a6
Create Date: 2026-09-01 12:00:00.000000

Written by hand: autogenerate turns a rename into a drop plus an add, which
would throw the values away. See RESSLab-Team/resslab-hub#276 and #244.

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "c3f7a91b2e08"
down_revision = "b7c1e2d4f5a6"
branch_labels = None
depends_on = None


def upgrade():
    # The values were always in GPa (around 181), only the name and the unit
    # said MPa.
    op.alter_column("material", "uvc_e__mpa_", new_column_name="uvc_e__gpa_")
    # Path to a raw data file nobody reads. It only confused contributors.
    op.drop_column("material", "file")
    # Drift from resslab-hub-data#50: the dictionary says DecimalFloat, the
    # model still said Numeric.
    op.alter_column(
        "residual_stress",
        "fy_e",
        type_=sa.Float(),
        existing_type=sa.Numeric(),
        existing_nullable=True,
    )


def downgrade():
    op.alter_column(
        "residual_stress",
        "fy_e",
        type_=sa.Numeric(),
        existing_type=sa.Float(),
        existing_nullable=True,
    )
    op.add_column("material", sa.Column("file", sa.String(), nullable=True))
    op.alter_column("material", "uvc_e__gpa_", new_column_name="uvc_e__mpa_")
