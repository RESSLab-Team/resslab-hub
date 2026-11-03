"""drop the parent id index of the curve tables

Every curve table has the primary key (<parent>_id, id), so Postgres already
uses that key for "WHERE <parent>_id = ...". The extra index on the parent id
only made each upload slower.

Revision ID: f5b9d3a7c2e4
Revises: e4a8c2f6b1d3
Create Date: 2026-11-03 10:05:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "f5b9d3a7c2e4"
down_revision = "e4a8c2f6b1d3"
branch_labels = None
depends_on = None

# curve table -> its parent id column
CURVE_TABLES = {
    "brace_displacement": "brace_id",
    "column_axial_shortening": "column_id",
    "column_moment_strong": "column_id",
    "column_moment_weak": "column_id",
    "connection_beam": "connection_id",
    "connection_beam_west": "connection_id",
    "connection_global": "connection_id",
    "connection_global_west": "connection_id",
    "connection_panel_zone": "connection_id",
    "ductile_fracture_epeq_simulation": "ductile_fracture_id",
    "ductile_fracture_force_elongation": "ductile_fracture_id",
    "ductile_fracture_force_elongation_simulation": "ductile_fracture_id",
    "ductile_fracture_force_radial": "ductile_fracture_id",
    "ductile_fracture_force_radial_simulation": "ductile_fracture_id",
    "ductile_fracture_lode_simulation": "ductile_fracture_id",
    "ductile_fracture_triax_simulation": "ductile_fracture_id",
    "eccentric_braced_frame_shear_link_angle": "eccentric_braced_frame_id",
    "hss_column_moment_rotation": "hss_column_id",
    "material_stress_strain": "material_id",
    "residual_stress_distribution_f1": "residual_stress_id",
    "residual_stress_distribution_f2": "residual_stress_id",
    "residual_stress_distribution_w1": "residual_stress_id",
    "residual_stress_qp_coefficient": "residual_stress_id",
    "tensile_coupon_stress_strain": "tensile_coupon_id",
}


def upgrade():
    for table, column in CURVE_TABLES.items():
        op.drop_index(op.f(f"ix_{table}_{column}"), table_name=table, if_exists=True)


def downgrade():
    for table, column in CURVE_TABLES.items():
        op.create_index(op.f(f"ix_{table}_{column}"), table, [column], unique=False)
