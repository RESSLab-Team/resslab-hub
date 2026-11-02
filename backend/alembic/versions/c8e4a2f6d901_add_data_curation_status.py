"""add data_curation_status to every main table

Revision ID: c8e4a2f6d901
Revises: b7d2e5f81c3a
Create Date: 2026-10-12 10:00:00.000000

The review status of a row (#253): `unverified` when a submission goes live,
`verified` once a curator checked it. The server default marks every row
already in the database as verified, which is what the data repository says
for them too; the next upload writes the real value.

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "c8e4a2f6d901"
down_revision = "b7d2e5f81c3a"
branch_labels = None
depends_on = None

TABLES = (
    "brace",
    "column",
    "connection",
    "hss_column",
    "eccentric_braced_frame",
    "material",
    "tensile_coupon",
    "ductile_fracture",
    "residual_stress",
)


def upgrade():
    for table in TABLES:
        op.add_column(
            table,
            sa.Column(
                "data_curation_status",
                sa.String(),
                server_default="verified",
                nullable=False,
            ),
        )


def downgrade():
    for table in TABLES:
        op.drop_column(table, "data_curation_status")
