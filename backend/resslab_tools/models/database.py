"""
Databse Models
"""
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Float,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    func,
    select,
)
from sqlalchemy.orm import column_property

from resslab_tools.utils.database import Base

DecimalFloat = Float(asdecimal=True)


class ConnectionGlobal(Base):
    """
    Global
    """

    __tablename__ = "connection_global"

    connection_id = Column(
        String, ForeignKey("connection.id"), primary_key=True, index=True
    )
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    story_drift_angle = Column(Numeric, nullable=False)
    actuator_force = Column(Numeric, nullable=False)


class ConnectionGlobalWest(Base):
    """
    Global
    """

    __tablename__ = "connection_global_west"

    connection_id = Column(
        String, ForeignKey("connection.id"), primary_key=True, index=True
    )
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    story_drift_angle = Column(Numeric, nullable=False)
    actuator_force = Column(Numeric, nullable=False)


class ConnectionPanelZone(Base):
    """
    Panel Zone
    """

    __tablename__ = "connection_panel_zone"

    connection_id = Column(
        String, ForeignKey("connection.id"), primary_key=True, index=True
    )
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    shear_distortion = Column(Numeric, nullable=False)
    shear_force = Column(Numeric, nullable=False)


class Connection(Base):
    """
    Connection
    """

    __tablename__ = "connection"

    id = Column(String, primary_key=True)
    experimental_program = Column(String, nullable=False)
    date = Column(SmallInteger, nullable=False)
    specimen_designation = Column(String, nullable=False)
    northridge = Column(String(4), nullable=False)
    specimen_type = Column(String, nullable=False)
    comments = Column(String)
    loading_protocol = Column(String, nullable=False)
    slab = Column(Boolean, nullable=False)
    connection_type = Column(String, nullable=False)
    t_pl = Column(DecimalFloat)
    rbs_cut = Column(DecimalFloat)
    s_h = Column(DecimalFloat)
    d_h = Column(DecimalFloat)
    section_b = Column(String, nullable=False)
    d_b = Column(Numeric, nullable=False)
    d_bg = Column(Numeric, nullable=False)
    t_bw = Column(Numeric, nullable=False)
    b_bf = Column(Numeric, nullable=False)
    t_bf = Column(Numeric, nullable=False)
    r_b = Column(Numeric, nullable=False)
    a_b = Column(Numeric, nullable=False)
    i_xb = Column(Numeric, nullable=False)
    z_xb = Column(Numeric, nullable=False)
    z_xb_bfp = Column(DecimalFloat)
    r_yb = Column(Numeric)
    b_fb_rbs = Column(DecimalFloat)
    d_gb_rbs = Column(DecimalFloat)
    a_b_rbs = Column(DecimalFloat)
    i_xb_rbs = Column(DecimalFloat)
    z_xb_rbs = Column(DecimalFloat)
    d_bm = Column(DecimalFloat)
    d_bgm = Column(DecimalFloat)
    t_bwm = Column(DecimalFloat)
    b_bfm = Column(DecimalFloat)
    t_bfm = Column(DecimalFloat)
    z_xbm = Column(DecimalFloat)
    steel_b = Column(String, nullable=False)
    f_yb = Column(Numeric, nullable=False)
    f_ybw = Column(DecimalFloat)
    f_ybf = Column(DecimalFloat)
    f_yb_mill = Column(DecimalFloat)
    f_yb_avg = Column(DecimalFloat)
    l_b = Column(Numeric, nullable=False)
    l_fc = Column(Numeric, nullable=False)
    l_o = Column(Numeric, nullable=False)
    lo_db = Column(Numeric, nullable=False)
    section_c = Column(String, nullable=False)
    d_c = Column(Numeric, nullable=False)
    t_cw = Column(Numeric, nullable=False)
    b_cf = Column(Numeric, nullable=False)
    c_c = Column(Numeric, nullable=False)
    t_cf = Column(Numeric, nullable=False)
    r_c = Column(Numeric, nullable=False)
    a_c = Column(Numeric, nullable=False)
    i_xc = Column(Numeric, nullable=False)
    d_cm = Column(DecimalFloat)
    t_wcm = Column(DecimalFloat)
    c_cm = Column(DecimalFloat)
    b_fcm = Column(DecimalFloat)
    t_fcm = Column(DecimalFloat)
    steel_c = Column(String, nullable=False)
    f_yc = Column(Numeric, nullable=False)
    f_ydp = Column(DecimalFloat)
    f_ycw = Column(DecimalFloat)
    f_ycf = Column(DecimalFloat)
    f_yc_mill = Column(DecimalFloat)
    fyc_avg = Column(DecimalFloat)
    h_c = Column(Numeric, nullable=False)
    backing_bar = Column(Boolean)
    electrode = Column(String)
    d_electrode = Column(String)
    cvn_0f = Column(String)
    cvn_minus20f = Column(String)
    cvn_70f = Column(String)
    access_hole_geometry = Column(String)
    section_shape_c = Column(String(1), nullable=False)
    d_pz = Column(Numeric, nullable=False)
    tw_pz = Column(Numeric, nullable=False)
    bf_pz = Column(Numeric, nullable=False)
    tf_pz = Column(Numeric, nullable=False)
    dz = Column(Numeric, nullable=False)
    zw = Column(Numeric, nullable=False)
    dz_plug = Column(DecimalFloat)
    wz_plug = Column(DecimalFloat)
    wd = Column(Numeric, nullable=False)
    n_dp = Column(SmallInteger, nullable=False)
    t_dp = Column(Numeric, nullable=False)
    t_dp_tot = column_property(t_dp * n_dp)
    t_p = Column(Numeric, nullable=False)
    t_cp = Column(Numeric, nullable=False)
    d_cp = Column(Numeric, nullable=False)
    db_plus = Column(Numeric, nullable=False)
    db_minus = Column(Numeric, nullable=False)
    a_vc = Column(Numeric, nullable=False)
    fy_pz_m = Column(Numeric)
    p_cm = Column(Numeric)
    n_pm = Column(Numeric)
    v_pz_el_m_europe = Column(DecimalFloat)
    r_n_el_m_aisc = Column(DecimalFloat)
    r_n_pl_m_aisc = Column(DecimalFloat)
    v_pz_m_aij = Column(DecimalFloat)
    fy_pz_n = Column(Numeric, nullable=False)
    p_cn = Column(Numeric, nullable=False)
    n_pn = Column(Numeric, nullable=False)
    v_pz_el_n_europe = Column(Numeric, nullable=False)
    r_n_el_n_aisc = Column(Numeric, nullable=False)
    r_n_pl_n_aisc = Column(Numeric, nullable=False)
    v_pz_n_aij = Column(Numeric, nullable=False)
    m_cf_minus_n = Column(Numeric)
    m_cf_plus_n = Column(Numeric)
    m_cf_minus_m = Column(DecimalFloat)
    m_cf_plus_m = Column(DecimalFloat)
    v_bf_plus_n = Column(Numeric, nullable=False)
    v_bf_minus_n = Column(Numeric, nullable=False)
    v_col_n = Column(Numeric, nullable=False)
    r_u_n = Column(Numeric)
    r_u_m = Column(DecimalFloat)
    ru_rn_el_n = Column(Numeric, nullable=False)
    ru_rn_pl_n = Column(Numeric, nullable=False)
    aisc_pz_violation_n = Column(Boolean, nullable=False)
    ru_rn_el_m = Column(DecimalFloat)
    ru_rn_pl_m = Column(DecimalFloat)
    aisc_pz_violation_m = Column(Boolean)
    g_max = Column(Numeric, nullable=False)
    g_y = Column(Numeric, nullable=False)
    g_max_g_y = Column(Numeric, nullable=False)
    reference = Column(String, nullable=False)

    global_count = column_property(
        select(func.count(ConnectionGlobal.id))
        .where(ConnectionGlobal.connection_id == id)
        .correlate_except(ConnectionGlobal)
        .scalar_subquery()  # type: ignore
    )
    global_west_count = column_property(
        select(func.count(ConnectionGlobalWest.id))
        .where(ConnectionGlobalWest.connection_id == id)
        .correlate_except(ConnectionGlobalWest)
        .scalar_subquery()  # type: ignore
    )
    panel_zone_count = column_property(
        select(func.count(ConnectionPanelZone.id))
        .where(ConnectionPanelZone.connection_id == id)
        .correlate_except(ConnectionPanelZone)
        .scalar_subquery()  # type: ignore
    )
