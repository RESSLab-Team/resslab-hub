"""add the built-up residual stresses

The residual stress database gets built-up sections (#228): 23 new columns
on ``residual_stress``, and a second format for the QP coefficient files.

- ``sym`` is mandatory. The rows already in the database are hot-rolled,
  which the data repo marks ``doubly``, so that is the server default.
- ``steel``, ``sigma_0_f`` and ``sigma_0_w`` become nullable: some built-up
  records have no flange or web measurement.
- ``sigma_0_f``, ``sigma_0_w``, ``plot_sf``, ``latitude`` and ``longitude`` go
  from numeric to double precision, like the other measured values
  (``DecimalFloat``), which is what the dictionary says now.
- ``residual_stress_qp_coefficient.name``: NULL for the four coefficients of a
  hot-rolled fit, the column name for each value of a built-up fit.

On the way down, the built-up QP rows go first: the old code reads every
row of the table as one of the four hot-rolled coefficients.

Revision ID: 3cba9f5e994c
Revises: b4d8f2a6c1e3
Create Date: 2026-11-26 14:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "3cba9f5e994c"
down_revision = "b4d8f2a6c1e3"
branch_labels = None
depends_on = None

TABLE = "residual_stress"
QP_TABLE = "residual_stress_qp_coefficient"

NEW_COLUMNS = (
    ("steel_web", sa.String()),
    ("fy_nw", sa.Float()),
    ("fy_ew", sa.Float()),
    ("b2", sa.Float()),
    ("tf2", sa.Float()),
    ("plt_cut_f", sa.String()),
    ("plt_cut_w", sa.String()),
    ("mea_met", sa.String()),
    ("weld_type", sa.String()),
    ("fillet_size", sa.Float()),
    ("weld_cur", sa.String()),
    ("weld_vol", sa.String()),
    ("weld_vel", sa.String()),
    ("preheat_c", sa.String()),
    ("interpass_c", sa.String()),
    ("holding_c", sa.String()),
    ("holding_t", sa.String()),
    ("n_weld_pass", sa.SmallInteger()),
    ("heat_inp", sa.String()),
    ("region", sa.String()),
    ("webdata", sa.SmallInteger()),
    ("sigma_0_b_f", sa.Float()),
)

NOW_NULLABLE = (
    ("steel", sa.String()),
    ("sigma_0_f", sa.Numeric()),
    ("sigma_0_w", sa.Numeric()),
)

NOW_FLOAT = ("sigma_0_f", "sigma_0_w", "plot_sf", "latitude", "longitude")


def upgrade():
    for name, type_ in NEW_COLUMNS:
        op.add_column(TABLE, sa.Column(name, type_, nullable=True))
    op.add_column(
        TABLE,
        sa.Column("sym", sa.String(), nullable=False, server_default="doubly"),
    )
    for name, type_ in NOW_NULLABLE:
        op.alter_column(TABLE, name, existing_type=type_, nullable=True)
    for name in NOW_FLOAT:
        op.alter_column(TABLE, name, existing_type=sa.Numeric(), type_=sa.Float())
    op.add_column(QP_TABLE, sa.Column("name", sa.String(), nullable=True))


def downgrade():
    op.execute(f"DELETE FROM {QP_TABLE} WHERE name IS NOT NULL")
    op.drop_column(QP_TABLE, "name")
    for name in NOW_FLOAT:
        op.alter_column(TABLE, name, existing_type=sa.Float(), type_=sa.Numeric())
    # The old columns were mandatory. An empty cell gets the values the old
    # uploader gave a "not reported" cell (NaN is the numeric one).
    op.execute(f"UPDATE {TABLE} SET steel = 'Not reported' WHERE steel IS NULL")
    for name in ("sigma_0_f", "sigma_0_w"):
        op.execute(f"UPDATE {TABLE} SET {name} = 'NaN' WHERE {name} IS NULL")
    for name, type_ in NOW_NULLABLE:
        op.alter_column(TABLE, name, existing_type=type_, nullable=False)
    op.drop_column(TABLE, "sym")
    for name, _ in reversed(NEW_COLUMNS):
        op.drop_column(TABLE, name)
