"""
API Models
"""

from datetime import date
from decimal import Decimal
from enum import Enum
from math import isnan
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, validator


def _change_nan_to_none(v: Optional[Decimal]) -> Optional[Decimal]:
    if v is not None and isnan(v):
        return None
    return v


class OrmModel(BaseModel):
    """
    Parent class for all API models
    """

    class Config:
        orm_mode = True


class ConnectionModel(BaseModel):
    """
    Connection
    """

    @validator("f_ybw", "f_ybf", "f_ycw", "f_ycf")
    def change_nan_to_none(cls, v) -> Optional[Decimal]:
        return _change_nan_to_none(v)

    # START_OF_GENERATED_CODE_connection
    id: str
    experimental_program: str
    date: int
    specimen_designation: str
    northridge: str
    specimen_type: str
    comments: Optional[str]
    loading_protocol: str
    slab: bool
    connection_type: str
    t_pl: Optional[Decimal]
    rbs_cut: Optional[Decimal]
    s_h: Optional[Decimal]
    d_h: Optional[Decimal]
    section_b: str
    d_b: Optional[Decimal]
    d_bg: Optional[Decimal]
    t_bw: Optional[Decimal]
    b_bf: Optional[Decimal]
    t_bf: Optional[Decimal]
    r_b: Optional[Decimal]
    a_b: Optional[Decimal]
    i_xb: Optional[Decimal]
    z_xb: Optional[Decimal]
    z_xb_bfp: Optional[Decimal]
    r_yb: Optional[Decimal]
    b_bf_rbs: Optional[Decimal]
    d_gb_rbs: Optional[Decimal]
    a_b_rbs: Optional[Decimal]
    i_xb_rbs: Optional[Decimal]
    z_xb_rbs: Optional[Decimal]
    d_bm: Optional[Decimal]
    d_bgm: Optional[Decimal]
    t_bwm: Optional[Decimal]
    b_bfm: Optional[Decimal]
    t_bfm: Optional[Decimal]
    z_xbm: Optional[Decimal]
    steel_b: str
    f_yb: Optional[Decimal]
    f_ybw: Optional[Decimal]
    f_ybf: Optional[Decimal]
    f_yb_mill: Optional[Decimal]
    f_yb_avg: Optional[Decimal]
    l_b: Optional[Decimal]
    l_fc: Optional[Decimal]
    l_o: Optional[Decimal]
    lo_db: Optional[Decimal]
    section_c: str
    d_c: Optional[Decimal]
    t_cw: Optional[Decimal]
    b_cf: Optional[Decimal]
    c_c: Optional[Decimal]
    t_cf: Optional[Decimal]
    r_c: Optional[Decimal]
    a_c: Optional[Decimal]
    i_xc: Optional[Decimal]
    d_cm: Optional[Decimal]
    t_wcm: Optional[Decimal]
    c_cm: Optional[Decimal]
    b_fcm: Optional[Decimal]
    t_fcm: Optional[Decimal]
    steel_c: str
    f_yc: Optional[Decimal]
    f_ydp: Optional[Decimal]
    f_ycw: Optional[Decimal]
    f_ycf: Optional[Decimal]
    f_yc_mill: Optional[Decimal]
    f_yc_avg: Optional[Decimal]
    h_c: Optional[Decimal]
    backing_bar: Optional[bool]
    electrode: str
    d_electrode: Optional[Decimal]
    cvn_0f: Optional[Decimal]
    cvn_minus20f: Optional[Decimal]
    cvn_70f: Optional[Decimal]
    access_hole_geometry: Optional[str]
    w: Optional[Decimal]
    w_l: Optional[Decimal]
    w_r: Optional[Decimal]
    h_t: Optional[Decimal]
    a_s: Optional[Decimal]
    f_sk: Optional[Decimal]
    f_sm: Optional[Decimal]
    h_co: Optional[Decimal]
    slab_con_type: Optional[str]
    f_ck: Optional[Decimal]
    f_cm: Optional[Decimal]
    cur_days: Optional[str]
    f_c_compr_calc: Optional[Decimal]
    d: Optional[Decimal]
    h_sc: Optional[Decimal]
    n_studs: Optional[int]
    n_diss: Optional[int]
    n_r: Optional[int]
    f_u_sc: Optional[Decimal]
    h_p: Optional[Decimal]
    b_o: Optional[Decimal]
    deck_ribs_orientation: Optional[str]
    section_shape_c: str
    d_pz: Optional[Decimal]
    tw_pz: Optional[Decimal]
    bf_pz: Optional[Decimal]
    tf_pz: Optional[Decimal]
    dz: Optional[Decimal]
    zw: Optional[Decimal]
    dz_plug: Optional[Decimal]
    wz_plug: Optional[Decimal]
    wd: Optional[Decimal]
    n_dp: Optional[int]
    t_dp: Optional[Decimal]
    t_dp_tot: Optional[Decimal]
    t_p: Optional[Decimal]
    t_cp: Optional[Decimal]
    d_cp: Optional[Decimal]
    db_plus: Optional[Decimal]
    db_minus: Optional[Decimal]
    a_vc: Optional[Decimal]
    fy_pz_m: Optional[Decimal]
    p_cm: Optional[Decimal]
    n_pm: Optional[Decimal]
    v_pz_el_m_europe: Optional[Decimal]
    r_n_el_m_aisc: Optional[Decimal]
    r_n_pl_m_aisc: Optional[Decimal]
    v_pz_m_aij: Optional[Decimal]
    fy_pz_n: Optional[Decimal]
    p_cn: Optional[Decimal]
    n_pn: Optional[Decimal]
    v_pz_el_n_europe: Optional[Decimal]
    r_n_el_n_aisc: Optional[Decimal]
    r_n_pl_n_aisc: Optional[Decimal]
    v_pz_n_aij: Optional[Decimal]
    m_cf_minus_n: Optional[Decimal]
    m_cf_plus_n: Optional[Decimal]
    m_cf_minus_m: Optional[Decimal]
    m_cf_plus_m: Optional[Decimal]
    v_bf_plus_n: Optional[Decimal]
    v_bf_minus_n: Optional[Decimal]
    v_col_n: Optional[Decimal]
    r_u_n: Optional[Decimal]
    r_u_m: Optional[Decimal]
    ru_rn_el_n: Optional[Decimal]
    ru_rn_pl_n: Optional[Decimal]
    aisc_pz_violation_n: Optional[bool]
    ru_rn_el_m: Optional[Decimal]
    ru_rn_pl_m: Optional[Decimal]
    aisc_pz_violation_m: Optional[bool]
    g_max: Optional[Decimal]
    g_y: Optional[Decimal]
    g_max_g_y: Optional[Decimal]
    reference: str
    link: Optional[str]
    latitude: Optional[Decimal]
    longitude: Decimal
    # END_OF_GENERATED_CODE_connection

    beam_count: int
    beam_west_count: int
    global_count: int
    global_west_count: int
    panel_zone_count: int

    global_west_count: int
    panel_zone_count: int


class CountModel(BaseModel):
    """
    Count
    """

    names: List[str]
    value: int


class RangeModel(BaseModel):
    """
    Range
    """

    min: Decimal
    max: Decimal


class DateRangeModel(BaseModel):
    """
    Date Range
    """

    min: date
    max: date


FieldsModel = Dict[str, Any]


class MatrixModel(BaseModel):
    ids: List[str]
    data: List[List[Optional[Union[Decimal, str]]]]


ConnectionField = Enum(
    "ConnectionField",
    {key: key for key in ConnectionModel.__fields__},
    module=__name__,
    type=str,
)

ConnectionNumberField = Enum(
    "ConnectionNumberField",
    {
        key: key
        for key, field in ConnectionModel.__fields__.items()
        if field.type_ in [Decimal, int]
    },
    module=__name__,
    type=str,
)


class ColumnModel(BaseModel):
    @validator("th_80")
    def change_nan_to_none(cls, v) -> Optional[Decimal]:
        return _change_nan_to_none(v)

    # START_OF_GENERATED_CODE_column
    id: str
    experimental_program: str
    date: int
    section_c: str
    specimen_designation: str
    d_c: Optional[Decimal]
    k_c: Optional[Decimal]
    k1_c: Optional[Decimal]
    h_c: Optional[Decimal]
    t_cw: Optional[Decimal]
    h_over_t_cw: Optional[Decimal]
    b_cf: Optional[Decimal]
    t_cf: Optional[Decimal]
    b_f_over_t_cf: Optional[Decimal]
    a_cm: Optional[Decimal]
    a_cn: Optional[Decimal]
    i_xb: Optional[Decimal]
    i_xc: Optional[Decimal]
    s_xc: Optional[Decimal]
    s_yc: Optional[Decimal]
    z_xc: Optional[Decimal]
    z_yc: Optional[Decimal]
    j_c: Optional[Decimal]
    c_wc: Optional[Decimal]
    r_yc: Optional[Decimal]
    r_xc: Optional[Decimal]
    l_c: Optional[Decimal]
    l_sc: Optional[Decimal]
    l_bc: Optional[Decimal]
    l_b_over_r_yc: Optional[Decimal]
    k_xc: Optional[Decimal]
    k_yc: Optional[Decimal]
    lambda_xc: Optional[Decimal]
    lambda_yc: Optional[Decimal]
    lambda_ltb: Optional[Decimal]
    steel_c: str
    r_y: Optional[Decimal]
    r_t: Optional[Decimal]
    f_ymf: Optional[Decimal]
    f_ymw: Optional[Decimal]
    f_umf: Optional[Decimal]
    f_umw: Optional[Decimal]
    f_yn: Optional[Decimal]
    f_un: Optional[Decimal]
    e_nc: Optional[Decimal]
    e_mc: Optional[Decimal]
    g_nc: Optional[Decimal]
    g_mc: Optional[Decimal]
    boundary_condition: str
    p_ym: Optional[Decimal]
    p_yn: Optional[Decimal]
    p_ye: Optional[Decimal]
    lateral_lp: str
    direction_lp: str
    axis_of_bending: str
    axial_lp: str
    p_g: Optional[Decimal]
    p_t: Optional[Decimal]
    p_c: Optional[Decimal]
    p_g_over_p_ym: Optional[Decimal]
    p_g_over_p_yn: Optional[Decimal]
    p_t_over_p_ym: Optional[Decimal]
    p_c_over_p_ym: Optional[Decimal]
    p_c_over_p_yn: Optional[Decimal]
    p: Optional[Decimal]
    t_top_plate: Optional[Decimal]
    t_bottom_plate: Optional[Decimal]
    test_procedure: str
    comments: Optional[str]
    k_test: Optional[Decimal]
    k_flexure_th: Optional[Decimal]
    k_shear_th: Optional[Decimal]
    k_theory: Optional[Decimal]
    th_y: Optional[Decimal]
    th_lb: Optional[Decimal]
    th_80: Optional[Decimal]
    th_50: Optional[Decimal]
    th_20: Optional[Decimal]
    th_1l: Optional[Decimal]
    th_2l: Optional[Decimal]
    th_3l: Optional[Decimal]
    th_4l: Optional[Decimal]
    th_6l: Optional[Decimal]
    d_80: Optional[Decimal]
    d_50: Optional[Decimal]
    d_20: Optional[Decimal]
    f_class_us: str
    w_class_us: str
    cs_class_us: str
    f_class_eu: str
    w_class_eu: str
    cs_class_eu: str
    cfe: bool
    reference: str
    link: Optional[str]
    latitude: Decimal
    longitude: Decimal
    # END_OF_GENERATED_CODE_column

    built_up: bool
    axial_shortening_count: int
    moment_strong_count: int
    moment_weak_count: int


ColumnField = Enum(
    "ColumnField",
    {key: key for key in ColumnModel.__fields__},
    module=__name__,
    type=str,
)

ColumnNumberField = Enum(
    "ColumnNumberField",
    {
        key: key
        for key, field in ColumnModel.__fields__.items()
        if field.type_ in [Decimal, int]
    },
    module=__name__,
    type=str,
)


class BraceModel(BaseModel):
    # START_OF_GENERATED_CODE_brace
    id: str
    investigator: str
    specimen_ID: str
    date: int
    cross_section_shape: str
    cross_section_size: str
    area: Optional[Decimal]
    d_br: Optional[Decimal]
    b_br: Optional[Decimal]
    t_br: Optional[Decimal]
    w_br: Optional[Decimal]
    i_x: Optional[Decimal]
    i_y: Optional[Decimal]
    r_x: Optional[Decimal]
    r_y: Optional[Decimal]
    z_x: Optional[Decimal]
    z_y: Optional[Decimal]
    j: Optional[Decimal]
    configuration: str
    brace_angle: Optional[Decimal]
    l_b: Optional[Decimal]
    l_b_clear: Optional[Decimal]
    steel: str
    e: Optional[Decimal]
    f_yn: Optional[Decimal]
    fy_m: Optional[Decimal]
    f_um: Optional[Decimal]
    boundary_condition: str
    l_1t: Optional[str]
    l_2t: Optional[str]
    l_3t: Optional[str]
    l_4t: Optional[Decimal]
    l_5t: Optional[str]
    l_6t: Optional[str]
    l_7t: Optional[str]
    _8t: Optional[Decimal]
    t_t: Optional[Decimal]
    l_1b: Optional[str]
    l_2b: Optional[str]
    l_3b: Optional[str]
    l_4b: Optional[str]
    l_5b: Optional[str]
    l_6b: Optional[str]
    l_7b: Optional[Decimal]
    l_8b: Optional[Decimal]
    t_b: Optional[str]
    steel_gp: Optional[str]
    f_yn_gp: Optional[Decimal]
    f_ym_gp: Optional[Decimal]
    f_um_gp: Optional[Decimal]
    weld_type: Optional[str]
    l_weld: Optional[Decimal]
    t_weld: Optional[Decimal]
    stick_space: Optional[Decimal]
    nub_bolts: Optional[Decimal]
    bolt_size: Optional[str]
    bolt_mat: Optional[str]
    reinforcement_pl: Optional[str]
    loading_protocol: str
    p_t: Optional[Decimal]
    p_t_theory: Optional[Decimal]
    p_c: Optional[Decimal]
    kl_r: Optional[Decimal]
    l_c: Optional[Decimal]
    l_c_theory: Optional[Decimal]
    k_assumed: Optional[Decimal]
    kl_r_theory: Optional[Decimal]
    reference: str
    link: Optional[str]
    latitude: Optional[Decimal]
    longitude: Optional[Decimal]
    # END_OF_GENERATED_CODE_brace

    displacement_count: int


BraceField = Enum(
    "BraceField",
    {key: key for key in BraceModel.__fields__},
    module=__name__,
    type=str,
)

BraceNumberField = Enum(
    "BraceNumberField",
    {
        key: key
        for key, field in BraceModel.__fields__.items()
        if field.type_ in [Decimal, int]
    },
    module=__name__,
    type=str,
)


class MaterialModel(BaseModel):
    # START_OF_GENERATED_CODE_material
    hidden_index: int
    experimental_program: str
    id: str
    profile_type: str
    profile: str
    source: str
    thickness: Decimal
    grade: str
    spec: Optional[str]
    lp: str
    size: str
    gage_length__mm_: Optional[Decimal]
    avg_reduced_dia__mm_: Optional[Decimal]
    avg_fractured_dia_top__mm_: Optional[Decimal]
    avg_fractured_dia_bot__mm_: Optional[Decimal]
    fy_n__mpa_: Optional[Decimal]
    fu_n__mpa_: Optional[Decimal]
    t_a__deg_c_: Optional[Decimal]
    date: date
    investigator: str
    location: str
    machine: str
    pid_force_k_p: Optional[Decimal]
    pid_force_t_i: Optional[Decimal]
    pid_force_t_d: Optional[Decimal]
    pid_disp_k_p: Optional[Decimal]
    pid_disp_t_i: Optional[Decimal]
    pid_disp_t_d: Optional[Decimal]
    pid_extenso_k_p: Optional[Decimal]
    pid_extenso_t_i: Optional[Decimal]
    pid_extenso_t_d: Optional[Decimal]
    yield_stress__mpa_: Optional[Decimal]
    elastic_modulus__mpa_: Optional[Decimal]
    fracture_strain: Optional[Decimal]
    c: Optional[Decimal]
    si: Optional[Decimal]
    mn: Optional[Decimal]
    p: Optional[Decimal]
    s: Optional[Decimal]
    n: Optional[Decimal]
    cu: Optional[Decimal]
    mo: Optional[Decimal]
    ni: Optional[Decimal]
    cr: Optional[Decimal]
    v: Optional[Decimal]
    nb: Optional[Decimal]
    ti: Optional[Decimal]
    al: Optional[Decimal]
    b: Optional[Decimal]
    zr: Optional[Decimal]
    sn: Optional[Decimal]
    ca: Optional[Decimal]
    h: Optional[Decimal]
    fe: Optional[Decimal]
    file: Optional[str]
    reference: Optional[str]
    link: Optional[str]
    latitude: Optional[Decimal]
    longitude: Optional[Decimal]
    citekey: Optional[str]
    uvc_phi__prct_: Optional[Decimal]
    uvc_e__mpa_: Optional[Decimal]
    uvc_sigma__mpa_: Optional[Decimal]
    uvc_q__mpa_: Optional[Decimal]
    uvc_b: Optional[Decimal]
    uvc_d__mpa_: Optional[Decimal]
    uvc_a: Optional[Decimal]
    uvc_c1__mpa_: Optional[Decimal]
    uvc_g1: Optional[Decimal]
    uvc_c2__mpa_: Optional[Decimal]
    uvc_g2: Optional[Decimal]
    hidden_dataset_index: int
    uvc_sigma_sat__mpa_: Optional[Decimal]
    uvc_sigma_hard__mpa_: Optional[Decimal]
    uvc_rho_yield: Optional[Decimal]
    uvc_rho_iso: Optional[Decimal]
    uvc_rho_kin: Optional[Decimal]
    uvc_rho_d: Optional[Decimal]
    # END_OF_GENERATED_CODE_material

    type: str
    year: int

    stress_strain_count: int


MaterialField = Enum(
    "MaterialField",
    {key: key for key in MaterialModel.__fields__},
    module=__name__,
    type=str,
)

MaterialNumberField = Enum(
    "MaterialNumberField",
    {
        key: key
        for key, field in MaterialModel.__fields__.items()
        if field.type_ in [Decimal, int]
    },
    module=__name__,
    type=str,
)

MaterialDateField = Enum(
    "MaterialDateField",
    {
        key: key
        for key, field in MaterialModel.__fields__.items()
        if field.type_ in [date]
    },
    module=__name__,
    type=str,
)


class ResidualStressModel(BaseModel):
    # START_OF_GENERATED_CODE_residual_stress
    id: str
    experimental_program: str
    date: int
    profile_type: str
    profile: str
    spec_var: Optional[str]
    steel: str
    fy_n: Optional[Decimal]
    fy_e: Optional[Decimal]
    fy_mf: Optional[Decimal]
    fy_mw: Optional[Decimal]
    h: Optional[Decimal]
    b: Optional[Decimal]
    tw: Optional[Decimal]
    tf: Optional[Decimal]
    r: Optional[Decimal]
    A: Optional[Decimal]
    sigma_0_f: Decimal
    sigma_0_w: Decimal
    flange_nr_data: int
    plot_sf: Decimal
    reference: str
    link: Optional[str]
    latitude: Optional[Decimal]
    longitude: Optional[Decimal]
    # END_OF_GENERATED_CODE_residual_stress

    qp_coefficient_count: int

    distribution_F1_count: int
    distribution_F2_count: int
    distribution_W1_count: int

    h_over_b: Decimal


ResidualStressField = Enum(
    "ResidualStressField",
    {key: key for key in ResidualStressModel.__fields__},
    module=__name__,
    type=str,
)

ResidualStressNumberField = Enum(
    "ResidualStressNumberField",
    {
        key: key
        for key, field in ResidualStressModel.__fields__.items()
        if field.type_ in [Decimal, int]
    },
    module=__name__,
    type=str,
)


class HSSColumnModel(BaseModel):
    # START_OF_GENERATED_CODE_hss_column
    id: str
    date: int
    investigator: str
    reference: str
    url: Optional[str]
    test_configuration: str
    stiffness_coefficient: int
    test_type: str
    loading_protocol: str
    forming_process: str
    seams: Optional[str]
    tube_section: str
    width__mm: Optional[Decimal]
    depth__mm: Optional[Decimal]
    flange_thickness__mm: Optional[Decimal]
    web_thickness__mm: Optional[Decimal]
    area__mm2: Optional[Decimal]
    moment_of_inertia__mm4: Optional[Decimal]
    radius__mm: Optional[Decimal]
    depth_over_t: Optional[Decimal]
    plastic_section_modulus__mm3: Optional[Decimal]
    axial_load_ratio: Optional[Decimal]
    axial_load_sequence: str
    loading_angle: Optional[int]
    steel_type: str
    fy_nominal__n_mm2: Optional[Decimal]
    fy_measured__n_mm2: Optional[Decimal]
    f_ultimate__n_mm2: Optional[Decimal]
    mp_measured__knmm: Optional[Decimal]
    length__mm: Optional[Decimal]
    ke_measured__knmm_rad: Optional[Decimal]
    my_pos_100fit__knmm: Optional[Decimal]
    my_neg_100fit__knmm: Optional[Decimal]
    theta_p_pos_100fit__rad: Optional[Decimal]
    theta_pc_pos_100fit__rad: Optional[Decimal]
    theta_u_pos_100fit__rad: Optional[Decimal]
    theta_p_neg_100fit__rad: Optional[Decimal]
    theta_pc_neg_100fit__rad: Optional[Decimal]
    theta_u_neg_100fit__rad: Optional[Decimal]
    mc_my_pos_100fit: Optional[Decimal]
    mu_mc_pos_100fit: Optional[Decimal]
    mc_my_neg_100fit: Optional[Decimal]
    mu_mc_neg_100fit: Optional[Decimal]
    my_pos_80fit__knmm: Optional[Decimal]
    my_neg_80fit__knmm: Optional[Decimal]
    theta_p_pos_80fit__rad: Optional[Decimal]
    theta_pc_pos_80fit__rad: Optional[Decimal]
    theta_u_pos_80fit__rad: Optional[Decimal]
    theta_p_neg_80fit__rad: Optional[Decimal]
    theta_pc_neg_80fit__rad: Optional[Decimal]
    theta_u_neg_80fit__rad: Optional[Decimal]
    mc_my_pos_80fit: Optional[Decimal]
    mu_mc_pos_80fit: Optional[Decimal]
    mc_my_neg_80fit: Optional[Decimal]
    mu_mc_neg_80fit: Optional[Decimal]
    lambda_s: Optional[Decimal]
    lambda_c: Optional[Decimal]
    flexural_buckling: str
    latitude: Optional[Decimal]
    longitude: Optional[Decimal]
    # END_OF_GENERATED_CODE_hss_column

    moment_rotation_count: int


HSSColumnField = Enum(
    "HSSColumnField",
    {key: key for key in HSSColumnModel.__fields__},
    module=__name__,
    type=str,
)

HSSColumnNumberField = Enum(
    "HSSColumnNumberField",
    {
        key: key
        for key, field in HSSColumnModel.__fields__.items()
        if field.type_ in [Decimal, int]
    },
    module=__name__,
    type=str,
)


class EccentricBracedFrameModel(BaseModel):
    # START_OF_GENERATED_CODE_eccentric_braced_frame
    id: str
    investigator: str
    year: int
    spec_id: str
    profile: str
    region: str
    sec_type: str
    sg_flg_link: str
    sg_web_link: str
    f_y_n_flg: Decimal
    f_y_n_web: Decimal
    f_u_n_flg: Decimal
    f_u_n_web: Decimal
    e_n_flg: int
    e_n_web: int
    f_y_m_flg: Optional[Decimal]
    f_y_m_web: Optional[Decimal]
    f_y_exp_l_flg: Optional[Decimal]
    f_y_exp_l_web: Optional[Decimal]
    f_u_m_flg: Optional[Decimal]
    f_u_m_web: Optional[Decimal]
    f_u_exp_l_flg: Optional[Decimal]
    f_u_exp_l_web: Optional[Decimal]
    e_m_flg: Optional[Decimal]
    e_m_web: Optional[Decimal]
    r_y_flg: Optional[Decimal]
    r_y_web: Optional[Decimal]
    r_t_flg: Optional[Decimal]
    r_t_web: Optional[Decimal]
    f_u_f_y_n_flg: Optional[Decimal]
    f_u_f_y_n_web: Optional[Decimal]
    f_u_f_y_m_flg: Optional[Decimal]
    f_u_f_y_m_web: Optional[Decimal]
    h_n: Decimal
    tw_n: Decimal
    bf_n: Decimal
    tf_n: Decimal
    tf_add_n: Optional[Decimal]
    r_n: Optional[Decimal]
    h_m: Optional[Decimal]
    tw_m: Optional[Decimal]
    bf_m: Optional[Decimal]
    tf_m: Optional[Decimal]
    tf_add_m: Optional[Decimal]
    hw_n: Decimal
    hw_m: Optional[Decimal]
    a_fil_n: Optional[Decimal]
    af_n: Decimal
    aw_n: Decimal
    a_n: Decimal
    af_m: Optional[Decimal]
    aw_m: Optional[Decimal]
    a_m: Optional[Decimal]
    zp_fil_n: Optional[Decimal]
    zp_n: Optional[Decimal]
    zp_no_fil_n: Optional[Decimal]
    zp_fil_m: Optional[Decimal]
    zp_m: Optional[Decimal]
    zp_no_fil_m: Optional[Decimal]
    link_loc: Optional[str]
    l_confi: Optional[str]
    l_con_typ: Optional[str]
    l_st: Optional[Decimal]
    h_st: Optional[Decimal]
    e: int
    l_con_confi: Optional[str]
    l_con_wld: Optional[str]
    l_endp_wld: Optional[str]
    l_bu_wld: Optional[str]
    l_s_side: Optional[str]
    l_s_reg: Optional[str]
    l_s_d_pnl_1_f: Optional[Decimal]
    l_s_d_pnl_2_f: Optional[Decimal]
    l_s_d_pnl_1_b: Optional[Decimal]
    l_s_d_pnl_2_b: Optional[Decimal]
    t_s: Optional[Decimal]
    l_s_weld: Optional[str]
    l_s_no_f: Optional[int]
    l_s_no_b: Optional[int]
    a_b_b: Optional[Decimal]
    t_e_s: Optional[Decimal]
    t_b_s: Optional[Decimal]
    d_b_s: Optional[Decimal]
    d_b_pnl_1: Optional[Decimal]
    d_b_pnl_2: Optional[Decimal]
    b_s_no: Optional[int]
    l_p_typ: str
    n_d_n_pl_ten: Optional[Decimal]
    n_d_n_pl_comp: Optional[Decimal]
    fail_mode: Optional[str]
    ov_aisc: Optional[Decimal]
    ov_ec8: Optional[Decimal]
    class_aisc: str
    class_ec8: str
    reference: str
    url: str
    latitude: Decimal
    longitude: Decimal
    # END_OF_GENERATED_CODE_eccentric_braced_frame

    shear_link_angle_count: int


EccentricBracedFrameField = Enum(
    "EccentricBracedFrameField",
    {key: key for key in EccentricBracedFrameModel.__fields__},
    module=__name__,
    type=str,
)

EccentricBracedFrameNumberField = Enum(
    "EccentricBracedFrameNumberField",
    {
        key: key
        for key, field in EccentricBracedFrameModel.__fields__.items()
        if field.type_ in [Decimal, int]
    },
    module=__name__,
    type=str,
)
