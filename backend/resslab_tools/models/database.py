"""
Databse Models
"""
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    func,
    select,
    text,
)
from sqlalchemy.orm import column_property

from resslab_tools.utils.database import Base

DecimalFloat = Float(asdecimal=True)


class ConnectionBeam(Base):  # type: ignore
    __tablename__ = "connection_beam"

    connection_id = Column(
        String, ForeignKey("connection.id"), primary_key=True, index=True
    )
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    chord_rotation = Column(Numeric, nullable=False)
    moment = Column(Numeric, nullable=False)


class ConnectionBeamWest(Base):  # type: ignore
    __tablename__ = "connection_beam_west"

    connection_id = Column(
        String, ForeignKey("connection.id"), primary_key=True, index=True
    )
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    chord_rotation = Column(Numeric, nullable=False)
    moment = Column(Numeric, nullable=False)


class ConnectionGlobal(Base):  # type: ignore
    __tablename__ = "connection_global"

    connection_id = Column(
        String, ForeignKey("connection.id"), primary_key=True, index=True
    )
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    story_drift_angle = Column(Numeric, nullable=False)
    actuator_force = Column(Numeric, nullable=False)


class ConnectionGlobalWest(Base):  # type: ignore
    __tablename__ = "connection_global_west"

    connection_id = Column(
        String, ForeignKey("connection.id"), primary_key=True, index=True
    )
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    story_drift_angle = Column(Numeric, nullable=False)
    actuator_force = Column(Numeric, nullable=False)


class ConnectionPanelZone(Base):  # type: ignore
    __tablename__ = "connection_panel_zone"

    connection_id = Column(
        String, ForeignKey("connection.id"), primary_key=True, index=True
    )
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    shear_distortion = Column(Numeric, nullable=False)
    shear_force = Column(Numeric, nullable=False)


class Connection(Base):  # type: ignore
    __tablename__ = "connection"

    id = Column(String, primary_key=True)
    experimental_program = Column(String, nullable=False)
    date = Column(SmallInteger, nullable=False)
    specimen_designation = Column(String, nullable=False)
    northridge = Column(String, nullable=False)
    specimen_type = Column(String, nullable=False)
    comments = Column(String)
    loading_protocol = Column(String, nullable=False)
    slab = Column(Boolean, nullable=False)
    connection_type = Column(String, nullable=False)
    t_pl = Column(Numeric)
    rbs_cut = Column(Numeric)
    s_h = Column(Numeric)
    d_h = Column(Numeric)
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
    z_xb_bfp = Column(Numeric)
    r_yb = Column(Numeric)
    b_fb_rbs = Column(Numeric)
    d_gb_rbs = Column(Numeric)
    a_b_rbs = Column(Numeric)
    i_xb_rbs = Column(Numeric)
    z_xb_rbs = Column(Numeric)
    d_bm = Column(DecimalFloat, nullable=False)
    d_bgm = Column(DecimalFloat, nullable=False)
    t_bwm = Column(DecimalFloat, nullable=False)
    b_bfm = Column(DecimalFloat, nullable=False)
    t_bfm = Column(DecimalFloat, nullable=False)
    z_xbm = Column(DecimalFloat, nullable=False)
    steel_b = Column(String, nullable=False)
    f_yb = Column(Numeric, nullable=False)
    f_ybw = Column(DecimalFloat, nullable=False)
    f_ybf = Column(DecimalFloat, nullable=False)
    f_yb_mill = Column(DecimalFloat)
    f_yb_avg = Column(Numeric)
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
    d_cm = Column(DecimalFloat, nullable=False)
    t_wcm = Column(DecimalFloat, nullable=False)
    c_cm = Column(DecimalFloat, nullable=False)
    b_fcm = Column(DecimalFloat, nullable=False)
    t_fcm = Column(DecimalFloat, nullable=False)
    steel_c = Column(String, nullable=False)
    f_yc = Column(Numeric, nullable=False)
    f_ydp = Column(DecimalFloat)
    f_ycw = Column(DecimalFloat, nullable=False)
    f_ycf = Column(DecimalFloat, nullable=False)
    f_yc_mill = Column(DecimalFloat, nullable=False)
    fyc_avg = Column(DecimalFloat)
    h_c = Column(Numeric, nullable=False)
    backing_bar = Column(Boolean)
    electrode = Column(String, nullable=False)
    d_electrode = Column(String, nullable=False)
    cvn_0f = Column(String, nullable=False)
    cvn_minus20f = Column(String, nullable=False)
    cvn_70f = Column(String, nullable=False)
    access_hole_geometry = Column(String)
    w = Column(Numeric)
    w_l = Column(Numeric)
    w_r = Column(Numeric)
    h_t = Column(Numeric)
    a_s = Column(Numeric)
    f_sk = Column(DecimalFloat)
    f_sm = Column(DecimalFloat)
    h_co = Column(Numeric)
    slab_con_type = Column(String)
    f_ck = Column(DecimalFloat)
    f_cm = Column(DecimalFloat)
    cur_days = Column(String)
    f_c_compr_calc = Column(Numeric)
    d = Column(Numeric)
    h_sc = Column(Numeric)
    n_studs = Column(SmallInteger)
    n_diss = Column(SmallInteger)
    n_r = Column(SmallInteger)
    f_u_sc = Column(Numeric)
    h_p = Column(Numeric)
    b_o = Column(Numeric)
    deck_ribs_orientation = Column(String)
    section_shape_c = Column(String, nullable=False)
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
    t_dp_tot = Column(Numeric, nullable=False)
    t_p = Column(Numeric, nullable=False)
    t_cp = Column(Numeric, nullable=False)
    d_cp = Column(Numeric, nullable=False)
    db_plus = Column(Numeric, nullable=False)
    db_minus = Column(Numeric, nullable=False)
    a_vc = Column(Numeric, nullable=False)
    fy_pz_m = Column(DecimalFloat)
    p_cm = Column(Numeric)
    n_pm = Column(Numeric)
    v_pz_el_m_europe = Column(Numeric)
    r_n_el_m_aisc = Column(Numeric)
    r_n_pl_m_aisc = Column(Numeric)
    v_pz_m_aij = Column(Numeric)
    fy_pz_n = Column(Numeric, nullable=False)
    p_cn = Column(Numeric, nullable=False)
    n_pn = Column(Numeric, nullable=False)
    v_pz_el_n_europe = Column(Numeric, nullable=False)
    r_n_el_n_aisc = Column(Numeric, nullable=False)
    r_n_pl_n_aisc = Column(Numeric, nullable=False)
    v_pz_n_aij = Column(Numeric, nullable=False)
    m_cf_minus_n = Column(Numeric)
    m_cf_plus_n = Column(Numeric)
    m_cf_minus_m = Column(Numeric)
    m_cf_plus_m = Column(Numeric)
    v_bf_plus_n = Column(Numeric, nullable=False)
    v_bf_minus_n = Column(Numeric, nullable=False)
    v_col_n = Column(Numeric, nullable=False)
    r_u_n = Column(Numeric)
    r_u_m = Column(Numeric)
    ru_rn_el_n = Column(Numeric, nullable=False)
    ru_rn_pl_n = Column(Numeric, nullable=False)
    aisc_pz_violation_n = Column(Boolean, nullable=False)
    ru_rn_el_m = Column(Numeric)
    ru_rn_pl_m = Column(Numeric)
    aisc_pz_violation_m = Column(Boolean)
    g_max = Column(Numeric, nullable=False)
    g_y = Column(Numeric, nullable=False)
    g_max_g_y = Column(Numeric, nullable=False)
    reference = Column(String, nullable=False)

    beam_count = column_property(
        select(func.count(ConnectionBeam.id))
        .where(ConnectionBeam.connection_id == id)
        .correlate_except(ConnectionBeam)
        .scalar_subquery()  # type: ignore
    )
    beam_west_count = column_property(
        select(func.count(ConnectionBeamWest.id))
        .where(ConnectionBeamWest.connection_id == id)
        .correlate_except(ConnectionBeamWest)
        .scalar_subquery()  # type: ignore
    )
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


class ColumnAxialShortening(Base):  # type: ignore
    __tablename__ = "column_axial_shortening"

    column_id = Column(String, ForeignKey("column.id"), primary_key=True, index=True)
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    chord_rotation = Column(Numeric, nullable=False)
    axial_shortening = Column(Numeric, nullable=False)


class ColumnMoment(Base):  # type: ignore
    __tablename__ = "column_moment"

    column_id = Column(String, ForeignKey("column.id"), primary_key=True, index=True)
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    chord_rotation = Column(Numeric, nullable=False)
    moment = Column(Numeric, nullable=False)


class ColumnEntity(Base):  # type: ignore
    __tablename__ = "column"

    id = Column(String, primary_key=True)
    experimental_program = Column(String, nullable=False)
    date = Column(SmallInteger, nullable=False)
    section_c = Column(String, nullable=False)
    specimen_designation = Column(String, nullable=False)
    d_c = Column(Numeric, nullable=False)
    k_c = Column(Numeric, nullable=False)
    k1_c = Column(Numeric, nullable=False)
    h_c = Column(Numeric, nullable=False)
    t_cw = Column(Numeric, nullable=False)
    h_over_t_cw = Column(Numeric, nullable=False)
    b_cf = Column(Numeric, nullable=False)
    t_cf = Column(Numeric, nullable=False)
    b_f_over_t_cf = Column(Numeric, nullable=False)
    a_cm = Column(Integer, nullable=False)
    a_cn = Column(Integer, nullable=False)
    i_xb = Column(BigInteger, nullable=False)
    i_xc = Column(Integer, nullable=False)
    s_xc = Column(Integer, nullable=False)
    s_yc = Column(Integer, nullable=False)
    z_xc = Column(Integer, nullable=False)
    z_yc = Column(Integer, nullable=False)
    j_c = Column(Integer, nullable=False)
    c_wc = Column(BigInteger, nullable=False)
    r_yc = Column(SmallInteger, nullable=False)
    r_xc = Column(SmallInteger, nullable=False)
    l_c = Column(SmallInteger, nullable=False)
    l_sc = Column(SmallInteger, nullable=False)
    l_bc = Column(SmallInteger, nullable=False)
    l_b_over_r_yc = Column(Numeric, nullable=False)
    k_xc = Column(Numeric, nullable=False)
    k_yc = Column(Numeric, nullable=False)
    lambda_xc = Column(SmallInteger, nullable=False)
    lambda_yc = Column(SmallInteger, nullable=False)
    lambda_ltb = Column(Numeric, nullable=False)
    steel_c = Column(String, nullable=False)
    r_y = Column(Numeric, nullable=False)
    r_t = Column(Numeric, nullable=False)
    f_ymf = Column(SmallInteger, nullable=False)
    f_ymw = Column(SmallInteger, nullable=False)
    f_umf = Column(SmallInteger, nullable=False)
    f_umw = Column(SmallInteger, nullable=False)
    f_yn = Column(SmallInteger, nullable=False)
    f_un = Column(SmallInteger, nullable=False)
    e_nc = Column(Integer, nullable=False)
    e_mc = Column(Integer, nullable=False)
    g_nc = Column(Integer, nullable=False)
    g_mc = Column(Integer, nullable=False)
    boundary_condition = Column(String, nullable=False)
    p_ym = Column(Integer, nullable=False)
    p_yn = Column(Integer, nullable=False)
    p_ye = Column(Integer, nullable=False)
    lateral_lp = Column(String, nullable=False)
    direction_lp = Column(String, nullable=False)
    axis_of_bending = Column(String, nullable=False)
    axial_lp = Column(String, nullable=False)
    p_g = Column(Integer, nullable=False)
    p_t = Column(Integer)
    p_c = Column(Integer, nullable=False)
    p_g_over_p_ym = Column(Numeric, nullable=False)
    p_g_over_p_yn = Column(Numeric, nullable=False)
    p_t_over_p_ym = Column(Numeric)
    p_c_over_p_ym = Column(Numeric, nullable=False)
    p_c_over_p_yn = Column(Numeric, nullable=False)
    p = Column(Integer, nullable=False)
    t_top_plate = Column(DecimalFloat, nullable=False)
    t_bottom_plate = Column(DecimalFloat, nullable=False)
    test_procedure = Column(String, nullable=False)
    comments = Column(String)
    k_test = Column(DecimalFloat, nullable=False)
    k_flexure_th = Column(SmallInteger, nullable=False)
    k_shear_th = Column(SmallInteger, nullable=False)
    k_theory = Column(SmallInteger, nullable=False)
    th_y = Column(DecimalFloat, nullable=False)
    th_lb = Column(DecimalFloat)
    th_80 = Column(DecimalFloat)
    th_50 = Column(DecimalFloat)
    th_20 = Column(DecimalFloat)
    th_1l = Column(DecimalFloat)
    th_2l = Column(DecimalFloat)
    th_3l = Column(DecimalFloat)
    th_4l = Column(DecimalFloat)
    th_6l = Column(DecimalFloat)
    d_80 = Column(DecimalFloat)
    d_50 = Column(DecimalFloat)
    d_20 = Column(DecimalFloat)
    f_class_us = Column(String, nullable=False)
    w_class_us = Column(String, nullable=False)
    cs_class_us = Column(String, nullable=False)
    f_class_eu = Column(String, nullable=False)
    w_class_eu = Column(String, nullable=False)
    cs_class_eu = Column(String, nullable=False)
    cfe = Column(Boolean, nullable=False)
    reference = Column(String, nullable=False)
    link = Column(String, nullable=False)

    built_up = column_property(section_c.ilike(text("'%built_up%'")))

    axial_shortening_count = column_property(
        select(func.count(ColumnAxialShortening.id))
        .where(ColumnAxialShortening.column_id == id)
        .correlate_except(ColumnAxialShortening)
        .scalar_subquery()  # type: ignore
    )
    moment_count = column_property(
        select(func.count(ColumnMoment.id))
        .where(ColumnMoment.column_id == id)
        .correlate_except(ColumnMoment)
        .scalar_subquery()  # type: ignore
    )


class BraceDisplacement(Base):  # type: ignore
    __tablename__ = "brace_displacement"

    brace_id = Column(String, ForeignKey("brace.id"), primary_key=True, index=True)
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    displacement = Column(Numeric, nullable=False)
    force = Column(Numeric, nullable=False)


class Brace(Base):  # type: ignore
    __tablename__ = "brace"

    id = Column(String, primary_key=True)
    investigator = Column(String, nullable=False)
    specimen_ID = Column(String, nullable=False)
    cross_section_shape = Column(String, nullable=False)
    cross_section_size = Column(String, nullable=False)
    area = Column(DecimalFloat, nullable=False)
    d_br = Column(DecimalFloat, nullable=False)
    b_br = Column(DecimalFloat)
    t_br = Column(DecimalFloat, nullable=False)
    w_br = Column(DecimalFloat)
    i_x = Column(DecimalFloat, nullable=False)
    i_y = Column(DecimalFloat, nullable=False)
    r_x = Column(DecimalFloat, nullable=False)
    r_y = Column(DecimalFloat, nullable=False)
    z_x = Column(String, nullable=False)
    z_y = Column(String, nullable=False)
    j = Column(DecimalFloat, nullable=False)
    configuration = Column(String, nullable=False)
    brace_angle = Column(DecimalFloat, nullable=False)
    l_b = Column(SmallInteger, nullable=False)
    l_b_clear = Column(SmallInteger, nullable=False)
    steel = Column(String, nullable=False)
    e = Column(Integer, nullable=False)
    f_yn = Column(DecimalFloat, nullable=False)
    fy_m = Column(DecimalFloat, nullable=False)
    f_um = Column(DecimalFloat, nullable=False)
    l_1t = Column(String)
    l_2t = Column(String)
    l_3t = Column(String)
    l_4t = Column(String)
    l_5t = Column(String)
    l_6t = Column(String)
    l_7t = Column(DecimalFloat)
    _8t = Column(DecimalFloat)
    t_t = Column(String)
    l_1b = Column(String)
    l_2b = Column(String)
    l_3b = Column(String)
    l_4b = Column(String)
    l_5b = Column(String)
    l_6b = Column(String)
    l_7b = Column(DecimalFloat)
    l_8b = Column(DecimalFloat)
    t_b = Column(String)
    steel_gp = Column(String)
    f_ym_gp = Column(DecimalFloat)
    f_um_gp = Column(DecimalFloat)
    weld_type = Column(String)
    l_weld = Column(DecimalFloat)
    t_weld = Column(DecimalFloat)
    stick_space = Column(DecimalFloat)
    nub_bolts = Column(String)
    bolt_size = Column(String)
    bolt_mat = Column(String)
    reinforcement_pl = Column(String)
    loading_protocol = Column(String, nullable=False)
    p_t = Column(String)
    p_t_theory = Column(String, nullable=False)
    p_c = Column(String)
    kl_r = Column(Numeric, nullable=False)
    l_c = Column(String, nullable=False)
    l_c_theory = Column(String, nullable=False)
    k_assumed = Column(DecimalFloat, nullable=False)
    kl_r_theory = Column(DecimalFloat, nullable=False)
    reference = Column(String, nullable=False)
    link = Column(String, nullable=False)

    displacement_count = column_property(
        select(func.count(BraceDisplacement.id))
        .where(BraceDisplacement.brace_id == id)
        .correlate_except(BraceDisplacement)
        .scalar_subquery()  # type: ignore
    )
