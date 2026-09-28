"""materialize_count_flags

Replace the live *_count column_property subqueries with physical 0/1
columns, backfilled here and maintained by the uploader from now on
(resslab_hub/data/count_flags.py).

Revision ID: 2a42de2d3438
Revises: 630367b7b682
Create Date: 2026-08-04 10:30:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "2a42de2d3438"
down_revision = "630367b7b682"
branch_labels = None
depends_on = None

# parent table -> {flag column -> (child table, FK column)}
# Deliberately inlined (no import from resslab_hub) so the migration stays
# valid if the models change later.
FLAGS = {
    "brace": {"displacement_count": ("brace_displacement", "brace_id")},
    "column": {
        "axial_shortening_count": ("column_axial_shortening", "column_id"),
        "moment_strong_count": ("column_moment_strong", "column_id"),
        "moment_weak_count": ("column_moment_weak", "column_id"),
    },
    "connection": {
        "beam_count": ("connection_beam", "connection_id"),
        "beam_west_count": ("connection_beam_west", "connection_id"),
        "global_count": ("connection_global", "connection_id"),
        "global_west_count": ("connection_global_west", "connection_id"),
        "panel_zone_count": ("connection_panel_zone", "connection_id"),
    },
    "material": {"stress_strain_count": ("material_stress_strain", "material_id")},
    "residual_stress": {
        "qp_coefficient_count": (
            "residual_stress_qp_coefficient",
            "residual_stress_id",
        ),
        "distribution_F1_count": (
            "residual_stress_distribution_f1",
            "residual_stress_id",
        ),
        "distribution_F2_count": (
            "residual_stress_distribution_f2",
            "residual_stress_id",
        ),
        "distribution_W1_count": (
            "residual_stress_distribution_w1",
            "residual_stress_id",
        ),
    },
    "hss_column": {
        "moment_rotation_count": ("hss_column_moment_rotation", "hss_column_id")
    },
    "eccentric_braced_frame": {
        "shear_link_angle_count": (
            "eccentric_braced_frame_shear_link_angle",
            "eccentric_braced_frame_id",
        )
    },
    "tensile_coupon": {
        "stress_strain_count": ("tensile_coupon_stress_strain", "tensile_coupon_id")
    },
    "ductile_fracture": {
        "force_elongation_count": (
            "ductile_fracture_force_elongation",
            "ductile_fracture_id",
        ),
        "force_elongation_simulation_count": (
            "ductile_fracture_force_elongation_simulation",
            "ductile_fracture_id",
        ),
        "force_radial_count": (
            "ductile_fracture_force_radial",
            "ductile_fracture_id",
        ),
        "force_radial_simulation_count": (
            "ductile_fracture_force_radial_simulation",
            "ductile_fracture_id",
        ),
        "epeq_simulation_count": (
            "ductile_fracture_epeq_simulation",
            "ductile_fracture_id",
        ),
        "lode_simulation_count": (
            "ductile_fracture_lode_simulation",
            "ductile_fracture_id",
        ),
        "triax_simulation_count": (
            "ductile_fracture_triax_simulation",
            "ductile_fracture_id",
        ),
    },
}


def upgrade():
    for parent, flags in FLAGS.items():
        for flag in flags:
            op.add_column(
                parent,
                sa.Column(flag, sa.SmallInteger(), nullable=False, server_default="0"),
            )
        sets = ", ".join(
            f'"{flag}" = CASE WHEN EXISTS '
            f'(SELECT 1 FROM "{child}" c WHERE c."{fk}" = p.id) '
            "THEN 1 ELSE 0 END"
            for flag, (child, fk) in flags.items()
        )
        op.execute(f'UPDATE "{parent}" AS p SET {sets}')


def downgrade():
    for parent, flags in FLAGS.items():
        for flag in flags:
            op.drop_column(parent, flag)
