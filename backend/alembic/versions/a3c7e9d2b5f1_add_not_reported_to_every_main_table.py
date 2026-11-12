"""add not_reported to every main table

Revision ID: a3c7e9d2b5f1
Revises: f5b9d3a7c2e4
Create Date: 2026-11-10 10:00:00.000000

The names of the number, date and yes/no columns whose CSV cell was `nr`
(#427). These columns store NULL for both `nr` and `na`, so without the list
nobody can say which one it was. The database already lost the difference,
so old rows start with an empty list: the next upload fills it.

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "a3c7e9d2b5f1"
down_revision = "f5b9d3a7c2e4"
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
                "not_reported",
                postgresql.ARRAY(sa.String()),
                server_default="{}",
                nullable=False,
            ),
        )


def downgrade():
    for table in TABLES:
        op.drop_column(table, "not_reported")
