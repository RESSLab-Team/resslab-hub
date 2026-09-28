"""Derived 0/1 ``*_count`` flags on the parent tables.

Each flag records whether a parent row has time-series data in one child
table. They are physical columns (cheap to read) rather than live
subqueries (which cost seconds per request on a cold database), so they
must be recomputed whenever child tables change — upload_all() does this
at the end of every upload. Rows written behind the uploader's back (e.g.
raw SQL) are healed by the next upload.
"""

from sqlalchemy import case, exists, select, update
from sqlalchemy.orm import Session

from resslab_hub.models.database.brace import Brace, BraceDisplacement
from resslab_hub.models.database.column import (
    ColumnAxialShortening,
    ColumnEntity,
    ColumnMomentStrong,
    ColumnMomentWeak,
)
from resslab_hub.models.database.connection import (
    Connection,
    ConnectionBeam,
    ConnectionBeamWest,
    ConnectionGlobal,
    ConnectionGlobalWest,
    ConnectionPanelZone,
)
from resslab_hub.models.database.ductile_fracture import (
    DuctileFracture,
    DuctileFractureEpeqSimulation,
    DuctileFractureForceElongation,
    DuctileFractureForceElongationSimulation,
    DuctileFractureForceRadial,
    DuctileFractureForceRadialSimulation,
    DuctileFractureLodeSimulation,
    DuctileFractureTriaxSimulation,
)
from resslab_hub.models.database.eccentric_braced_frame import (
    EccentricBracedFrame,
    EccentricBracedFrameShearLinkAngle,
)
from resslab_hub.models.database.hss_column import HSSColumn, HSSColumnMomentRotation
from resslab_hub.models.database.material import Material, MaterialStressStrain
from resslab_hub.models.database.residual_stress import (
    ResidualStress,
    ResidualStressDistributionF1,
    ResidualStressDistributionF2,
    ResidualStressDistributionW1,
    ResidualStressQPCoefficient,
)
from resslab_hub.models.database.tensile_coupon import (
    TensileCoupon,
    TensileCouponStressStrain,
)

# parent model -> {flag column name -> child FK column pointing at parent.id}
COUNT_FLAGS = {
    Brace: {"displacement_count": BraceDisplacement.brace_id},
    ColumnEntity: {
        "axial_shortening_count": ColumnAxialShortening.column_id,
        "moment_strong_count": ColumnMomentStrong.column_id,
        "moment_weak_count": ColumnMomentWeak.column_id,
    },
    Connection: {
        "beam_count": ConnectionBeam.connection_id,
        "beam_west_count": ConnectionBeamWest.connection_id,
        "global_count": ConnectionGlobal.connection_id,
        "global_west_count": ConnectionGlobalWest.connection_id,
        "panel_zone_count": ConnectionPanelZone.connection_id,
    },
    Material: {"stress_strain_count": MaterialStressStrain.material_id},
    ResidualStress: {
        "qp_coefficient_count": ResidualStressQPCoefficient.residual_stress_id,
        "distribution_F1_count": ResidualStressDistributionF1.residual_stress_id,
        "distribution_F2_count": ResidualStressDistributionF2.residual_stress_id,
        "distribution_W1_count": ResidualStressDistributionW1.residual_stress_id,
    },
    HSSColumn: {"moment_rotation_count": HSSColumnMomentRotation.hss_column_id},
    EccentricBracedFrame: {
        "shear_link_angle_count": EccentricBracedFrameShearLinkAngle.eccentric_braced_frame_id  # noqa: E501
    },
    TensileCoupon: {"stress_strain_count": TensileCouponStressStrain.tensile_coupon_id},
    DuctileFracture: {
        "force_elongation_count": DuctileFractureForceElongation.ductile_fracture_id,
        "force_elongation_simulation_count": DuctileFractureForceElongationSimulation.ductile_fracture_id,  # noqa: E501
        "force_radial_count": DuctileFractureForceRadial.ductile_fracture_id,
        "force_radial_simulation_count": DuctileFractureForceRadialSimulation.ductile_fracture_id,  # noqa: E501
        "epeq_simulation_count": DuctileFractureEpeqSimulation.ductile_fracture_id,
        "lode_simulation_count": DuctileFractureLodeSimulation.ductile_fracture_id,
        "triax_simulation_count": DuctileFractureTriaxSimulation.ductile_fracture_id,
    },
}


def recompute_count_flags(session: Session) -> None:
    """Set every parent's flags from the current child-table contents.

    One UPDATE per parent table; the EXISTS probes resolve on the child
    (fk, id) primary-key indexes. Idempotent.
    """
    for parent, flags in COUNT_FLAGS.items():
        session.execute(
            update(parent).values(
                {
                    name: case((exists(select(1).where(fk == parent.id)), 1), else_=0)
                    for name, fk in flags.items()
                }
            )
        )
