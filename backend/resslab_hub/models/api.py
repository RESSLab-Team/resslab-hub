"""
API Models
"""

from datetime import date
from decimal import Decimal
from enum import Enum
from math import isnan
from typing import Any, Dict, List, Optional, Union, get_args, get_origin

from pydantic import BaseModel, ConfigDict, field_validator, model_serializer


def _change_nan_to_none(
    v: Optional[Union[float, Decimal]],
) -> Optional[Union[float, Decimal]]:
    if v is not None and isnan(v):
        return None
    return v


def _field_base_type(field: Any) -> Any:
    """Underlying type of a model field, unwrapping ``Optional[...]``.

    Pydantic v2 exposes the full annotation (e.g. ``Optional[Decimal]``) on
    ``FieldInfo.annotation``; v1 exposed the unwrapped inner type on ``.type_``.
    """
    annotation = field.annotation
    if get_origin(annotation) is Union:
        args = [arg for arg in get_args(annotation) if arg is not type(None)]
        if len(args) == 1:
            return args[0]
    return annotation


class OrmModel(BaseModel):
    """
    Parent class for all API models
    """

    model_config = ConfigDict(from_attributes=True)


def _decimals_to_numbers(value: Any) -> Any:
    """Recursively convert ``Decimal`` leaves to JSON numbers (NaN -> None).

    Float NaN (the database's "not reported" sentinel) also becomes None —
    ``json.dumps`` would otherwise emit a bare ``NaN``, which is invalid JSON.
    Recurses through ``list`` so nested structures (e.g. ``MatrixModel.data``,
    a ``List[List[Decimal | str]]``) are handled; all other values pass through.
    """
    if isinstance(value, Decimal):
        return None if isnan(value) else float(value)
    if isinstance(value, float):
        return None if isnan(value) else value
    if isinstance(value, list):
        return [_decimals_to_numbers(item) for item in value]
    return value


class ApiModel(BaseModel):
    """Base for response models.

    Pydantic v2 serializes ``Decimal`` as a JSON *string*, but the OpenAPI
    contract and the frontend expect a number. Emit Decimals as JSON numbers
    (NaN -> null) at serialization time, leaving the field *types* as ``Decimal``
    so the type introspection in this module (the ``_field_base_type`` checks)
    keeps working.
    """

    @model_serializer(mode="wrap")
    def _decimals_as_numbers(self, handler: Any) -> Any:
        data = handler(self)
        if isinstance(data, dict):
            for name, value in self:
                if name in data and (
                    isinstance(value, (Decimal, list))
                    or (isinstance(value, float) and isnan(value))
                ):
                    data[name] = _decimals_to_numbers(value)
        return data


class ConnectionModel(ApiModel):
    """
    Connection
    """

    @field_validator("f_ybw", "f_ybf", "f_ycw", "f_ycf")
    @classmethod
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
    t_pl: Optional[float]
    rbs_cut: Optional[float]
    s_h: Optional[float]
    d_h: Optional[float]
    section_b: str
    d_b: Optional[float]
    d_bg: Optional[float]
    t_bw: Optional[float]
    b_bf: Optional[float]
    t_bf: Optional[float]
    r_b: Optional[float]
    a_b: Optional[float]
    i_xb: Optional[float]
    z_xb: Optional[float]
    z_xb_bfp: Optional[float]
    r_yb: Optional[float]
    b_bf_rbs: Optional[float]
    d_gb_rbs: Optional[float]
    a_b_rbs: Optional[float]
    i_xb_rbs: Optional[float]
    z_xb_rbs: Optional[float]
    d_bm: Optional[float]
    d_bgm: Optional[float]
    t_bwm: Optional[float]
    b_bfm: Optional[float]
    t_bfm: Optional[float]
    z_xbm: Optional[float]
    steel_b: str
    f_yb: Optional[float]
    f_ybw: Optional[float]
    f_ybf: Optional[float]
    f_yb_mill: Optional[float]
    f_yb_avg: Optional[float]
    l_b: Optional[float]
    l_fc: Optional[float]
    l_o: Optional[float]
    lo_db: Optional[float]
    section_c: str
    d_c: Optional[float]
    t_cw: Optional[float]
    b_cf: Optional[float]
    c_c: Optional[float]
    t_cf: Optional[float]
    r_c: Optional[float]
    a_c: Optional[float]
    i_xc: Optional[float]
    d_cm: Optional[float]
    t_wcm: Optional[float]
    c_cm: Optional[float]
    b_fcm: Optional[float]
    t_fcm: Optional[float]
    steel_c: str
    f_yc: Optional[float]
    f_ydp: Optional[float]
    f_ycw: Optional[float]
    f_ycf: Optional[float]
    f_yc_mill: Optional[float]
    f_yc_avg: Optional[float]
    h_c: Optional[float]
    backing_bar: Optional[bool]
    electrode: str
    d_electrode: Optional[float]
    cvn_0f: Optional[float]
    cvn_minus20f: Optional[float]
    cvn_70f: Optional[float]
    access_hole_geometry: Optional[str]
    w: Optional[float]
    w_l: Optional[float]
    w_r: Optional[float]
    h_t: Optional[float]
    a_s: Optional[float]
    f_sk: Optional[float]
    f_sm: Optional[float]
    h_co: Optional[float]
    slab_con_type: Optional[str]
    f_ck: Optional[float]
    f_cm: Optional[float]
    cur_days: Optional[str]
    f_c_compr_calc: Optional[float]
    d: Optional[float]
    h_sc: Optional[float]
    n_studs: Optional[int]
    n_diss: Optional[int]
    n_r: Optional[int]
    f_u_sc: Optional[float]
    h_p: Optional[float]
    b_o: Optional[float]
    deck_ribs_orientation: Optional[str]
    section_shape_c: str
    d_pz: Optional[float]
    tw_pz: Optional[float]
    bf_pz: Optional[float]
    tf_pz: Optional[float]
    dz: Optional[float]
    zw: Optional[float]
    dz_plug: Optional[float]
    wz_plug: Optional[float]
    wd: Optional[float]
    n_dp: Optional[int]
    t_dp: Optional[float]
    t_dp_tot: Optional[float]
    t_p: Optional[float]
    t_cp: Optional[float]
    d_cp: Optional[float]
    db_plus: Optional[float]
    db_minus: Optional[float]
    a_vc: Optional[float]
    fy_pz_m: Optional[float]
    p_cm: Optional[float]
    n_pm: Optional[float]
    v_pz_el_m_europe: Optional[float]
    r_n_el_m_aisc: Optional[float]
    r_n_pl_m_aisc: Optional[float]
    v_pz_m_aij: Optional[float]
    fy_pz_n: Optional[float]
    p_cn: Optional[float]
    n_pn: Optional[float]
    v_pz_el_n_europe: Optional[float]
    r_n_el_n_aisc: Optional[float]
    r_n_pl_n_aisc: Optional[float]
    v_pz_n_aij: Optional[float]
    m_cf_minus_n: Optional[float]
    m_cf_plus_n: Optional[float]
    m_cf_minus_m: Optional[float]
    m_cf_plus_m: Optional[float]
    v_bf_plus_n: Optional[float]
    v_bf_minus_n: Optional[float]
    v_col_n: Optional[float]
    r_u_n: Optional[float]
    r_u_m: Optional[float]
    ru_rn_el_n: Optional[float]
    ru_rn_pl_n: Optional[float]
    aisc_pz_violation_n: Optional[bool]
    ru_rn_el_m: Optional[float]
    ru_rn_pl_m: Optional[float]
    aisc_pz_violation_m: Optional[bool]
    g_max: Optional[float]
    g_y: Optional[float]
    g_max_g_y: Optional[float]
    reference: str
    link: Optional[str]
    latitude: Optional[float]
    longitude: float
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


class RangeModel(ApiModel):
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


class DictionaryColumnModel(BaseModel):
    """
    One column of a database's data dictionary.
    Field names match the frontend's DictColumn shape.
    """

    name: str
    description: str
    symbol: str
    unit: str
    type: str
    example: str
    nullable: bool


FieldsModel = Dict[str, Any]


class MatrixModel(ApiModel):
    ids: List[str]
    data: List[List[Optional[Union[Decimal, str]]]]


ConnectionField = Enum(
    "ConnectionField",
    {key: key for key in ConnectionModel.model_fields},
    module=__name__,
    type=str,
)

ConnectionNumberField = Enum(
    "ConnectionNumberField",
    {
        key: key
        for key, field in ConnectionModel.model_fields.items()
        if _field_base_type(field) in [Decimal, float, int]
    },
    module=__name__,
    type=str,
)


class ColumnModel(ApiModel):
    @field_validator("th_80")
    @classmethod
    def change_nan_to_none(cls, v) -> Optional[Decimal]:
        return _change_nan_to_none(v)

    # START_OF_GENERATED_CODE_column
    id: str
    experimental_program: str
    date: int
    section_c: str
    specimen_designation: str
    d_c: Optional[float]
    k_c: Optional[float]
    k1_c: Optional[float]
    h_c: Optional[float]
    t_cw: Optional[float]
    h_over_t_cw: Optional[float]
    b_cf: Optional[float]
    t_cf: Optional[float]
    b_f_over_t_cf: Optional[float]
    a_cm: Optional[float]
    a_cn: Optional[float]
    i_xb: Optional[float]
    i_xc: Optional[float]
    s_xc: Optional[float]
    s_yc: Optional[float]
    z_xc: Optional[float]
    z_yc: Optional[float]
    j_c: Optional[float]
    c_wc: Optional[float]
    r_yc: Optional[float]
    r_xc: Optional[float]
    l_c: Optional[float]
    l_sc: Optional[float]
    l_bc: Optional[float]
    l_b_over_r_yc: Optional[float]
    k_xc: Optional[float]
    k_yc: Optional[float]
    lambda_xc: Optional[float]
    lambda_yc: Optional[float]
    lambda_ltb: Optional[float]
    steel_c: str
    r_y: Optional[float]
    r_t: Optional[float]
    f_ymf: Optional[float]
    f_ymw: Optional[float]
    f_umf: Optional[float]
    f_umw: Optional[float]
    f_yn: Optional[float]
    f_un: Optional[float]
    e_nc: Optional[float]
    e_mc: Optional[float]
    g_nc: Optional[float]
    g_mc: Optional[float]
    boundary_condition: str
    p_ym: Optional[float]
    p_yn: Optional[float]
    p_ye: Optional[float]
    lateral_lp: str
    direction_lp: str
    axis_of_bending: str
    axial_lp: str
    p_g: Optional[float]
    p_t: Optional[float]
    p_c: Optional[float]
    p_g_over_p_ym: Optional[float]
    p_g_over_p_yn: Optional[float]
    p_t_over_p_ym: Optional[float]
    p_c_over_p_ym: Optional[float]
    p_c_over_p_yn: Optional[float]
    p: Optional[float]
    t_top_plate: Optional[float]
    t_bottom_plate: Optional[float]
    test_procedure: str
    comments: Optional[str]
    k_test: Optional[float]
    k_flexure_th: Optional[float]
    k_shear_th: Optional[float]
    k_theory: Optional[float]
    th_y: Optional[float]
    th_lb: Optional[float]
    th_80: Optional[float]
    th_50: Optional[float]
    th_20: Optional[float]
    th_1l: Optional[float]
    th_2l: Optional[float]
    th_3l: Optional[float]
    th_4l: Optional[float]
    th_6l: Optional[float]
    d_80: Optional[float]
    d_50: Optional[float]
    d_20: Optional[float]
    f_class_us: str
    w_class_us: str
    cs_class_us: str
    f_class_eu: str
    w_class_eu: str
    cs_class_eu: str
    cfe: bool
    reference: str
    link: Optional[str]
    latitude: float
    longitude: float
    # END_OF_GENERATED_CODE_column

    built_up: bool
    axial_shortening_count: int
    moment_strong_count: int
    moment_weak_count: int


ColumnField = Enum(
    "ColumnField",
    {key: key for key in ColumnModel.model_fields},
    module=__name__,
    type=str,
)

ColumnNumberField = Enum(
    "ColumnNumberField",
    {
        key: key
        for key, field in ColumnModel.model_fields.items()
        if _field_base_type(field) in [Decimal, float, int]
    },
    module=__name__,
    type=str,
)


class BraceModel(ApiModel):
    # START_OF_GENERATED_CODE_brace
    id: str
    investigator: str
    specimen_ID: str
    date: int
    cross_section_shape: str
    cross_section_size: str
    area: Optional[float]
    d_br: Optional[float]
    b_br: Optional[float]
    t_br: Optional[float]
    w_br: Optional[float]
    i_x: Optional[float]
    i_y: Optional[float]
    r_x: Optional[float]
    r_y: Optional[float]
    z_x: Optional[float]
    z_y: Optional[float]
    j: Optional[float]
    configuration: str
    brace_angle: Optional[float]
    l_b: Optional[float]
    l_b_clear: Optional[float]
    steel: str
    e: Optional[float]
    f_yn: Optional[float]
    fy_m: Optional[float]
    f_um: Optional[float]
    boundary_condition: str
    l_1t: Optional[str]
    l_2t: Optional[str]
    l_3t: Optional[str]
    l_4t: Optional[float]
    l_5t: Optional[str]
    l_6t: Optional[str]
    l_7t: Optional[str]
    _8t: Optional[float]
    t_t: Optional[float]
    l_1b: Optional[str]
    l_2b: Optional[str]
    l_3b: Optional[str]
    l_4b: Optional[str]
    l_5b: Optional[str]
    l_6b: Optional[str]
    l_7b: Optional[float]
    l_8b: Optional[float]
    t_b: Optional[str]
    steel_gp: Optional[str]
    f_yn_gp: Optional[float]
    f_ym_gp: Optional[float]
    f_um_gp: Optional[float]
    weld_type: Optional[str]
    l_weld: Optional[float]
    t_weld: Optional[float]
    stick_space: Optional[float]
    nub_bolts: Optional[float]
    bolt_size: Optional[str]
    bolt_mat: Optional[str]
    reinforcement_pl: Optional[str]
    loading_protocol: str
    p_t: Optional[float]
    p_t_theory: Optional[float]
    p_c: Optional[float]
    kl_r: Optional[float]
    l_c: Optional[float]
    l_c_theory: Optional[float]
    k_assumed: Optional[float]
    kl_r_theory: Optional[float]
    reference: str
    link: Optional[str]
    latitude: Optional[Decimal]
    longitude: Optional[Decimal]
    # END_OF_GENERATED_CODE_brace

    displacement_count: int


BraceField = Enum(
    "BraceField",
    {key: key for key in BraceModel.model_fields},
    module=__name__,
    type=str,
)

BraceNumberField = Enum(
    "BraceNumberField",
    {
        key: key
        for key, field in BraceModel.model_fields.items()
        if _field_base_type(field) in [Decimal, float, int]
    },
    module=__name__,
    type=str,
)


class MaterialModel(ApiModel):
    # START_OF_GENERATED_CODE_material
    hidden_index: int
    experimental_program: str
    id: str
    profile_type: str
    profile: str
    source: str
    thickness: float
    grade: str
    spec: Optional[str]
    lp: str
    size: str
    gage_length__mm_: Optional[float]
    avg_reduced_dia__mm_: Optional[float]
    avg_fractured_dia_top__mm_: Optional[float]
    avg_fractured_dia_bot__mm_: Optional[float]
    fy_n__mpa_: Optional[float]
    fu_n__mpa_: Optional[float]
    t_a__deg_c_: Optional[float]
    date: date
    investigator: str
    location: str
    machine: str
    pid_force_k_p: Optional[float]
    pid_force_t_i: Optional[float]
    pid_force_t_d: Optional[float]
    pid_disp_k_p: Optional[float]
    pid_disp_t_i: Optional[float]
    pid_disp_t_d: Optional[float]
    pid_extenso_k_p: Optional[float]
    pid_extenso_t_i: Optional[float]
    pid_extenso_t_d: Optional[float]
    yield_stress__mpa_: Optional[float]
    elastic_modulus__mpa_: Optional[float]
    fracture_strain: Optional[float]
    c: Optional[float]
    si: Optional[float]
    mn: Optional[float]
    p: Optional[float]
    s: Optional[float]
    n: Optional[float]
    cu: Optional[float]
    mo: Optional[float]
    ni: Optional[float]
    cr: Optional[float]
    v: Optional[float]
    nb: Optional[float]
    ti: Optional[float]
    al: Optional[float]
    b: Optional[float]
    zr: Optional[float]
    sn: Optional[float]
    ca: Optional[float]
    h: Optional[float]
    fe: Optional[float]
    file: Optional[str]
    reference: Optional[str]
    link: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    citekey: Optional[str]
    uvc_phi__prct_: Optional[float]
    uvc_e__mpa_: Optional[float]
    uvc_sigma__mpa_: Optional[float]
    uvc_q__mpa_: Optional[float]
    uvc_b: Optional[float]
    uvc_d__mpa_: Optional[float]
    uvc_a: Optional[float]
    uvc_c1__mpa_: Optional[float]
    uvc_g1: Optional[float]
    uvc_c2__mpa_: Optional[float]
    uvc_g2: Optional[float]
    hidden_dataset_index: int
    uvc_sigma_sat__mpa_: Optional[float]
    uvc_sigma_hard__mpa_: Optional[float]
    uvc_rho_yield: Optional[float]
    uvc_rho_iso: Optional[float]
    uvc_rho_kin: Optional[float]
    uvc_rho_d: Optional[float]
    # END_OF_GENERATED_CODE_material

    type: str
    year: int

    stress_strain_count: int


MaterialField = Enum(
    "MaterialField",
    {key: key for key in MaterialModel.model_fields},
    module=__name__,
    type=str,
)

MaterialNumberField = Enum(
    "MaterialNumberField",
    {
        key: key
        for key, field in MaterialModel.model_fields.items()
        if _field_base_type(field) in [Decimal, float, int]
    },
    module=__name__,
    type=str,
)

MaterialDateField = Enum(
    "MaterialDateField",
    {
        key: key
        for key, field in MaterialModel.model_fields.items()
        if _field_base_type(field) in [date]
    },
    module=__name__,
    type=str,
)


class ResidualStressModel(ApiModel):
    # START_OF_GENERATED_CODE_residual_stress
    id: str
    experimental_program: str
    date: int
    profile_type: str
    profile: str
    spec_var: Optional[str]
    steel: str
    fy_n: Optional[float]
    fy_e: Optional[Decimal]
    fy_mf: Optional[float]
    fy_mw: Optional[float]
    h: Optional[float]
    b: Optional[float]
    tw: Optional[float]
    tf: Optional[float]
    r: Optional[float]
    A: Optional[float]
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
    {key: key for key in ResidualStressModel.model_fields},
    module=__name__,
    type=str,
)

ResidualStressNumberField = Enum(
    "ResidualStressNumberField",
    {
        key: key
        for key, field in ResidualStressModel.model_fields.items()
        if _field_base_type(field) in [Decimal, float, int]
    },
    module=__name__,
    type=str,
)


class HSSColumnModel(ApiModel):
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
    width__mm: Optional[float]
    depth__mm: Optional[float]
    flange_thickness__mm: Optional[float]
    web_thickness__mm: Optional[float]
    area__mm2: Optional[float]
    moment_of_inertia__mm4: Optional[float]
    radius__mm: Optional[float]
    depth_over_t: Optional[float]
    plastic_section_modulus__mm3: Optional[float]
    axial_load_ratio: Optional[float]
    axial_load_sequence: str
    loading_angle: Optional[int]
    steel_type: str
    fy_nominal__n_mm2: Optional[float]
    fy_measured__n_mm2: Optional[float]
    f_ultimate__n_mm2: Optional[float]
    mp_measured__knmm: Optional[float]
    length__mm: Optional[float]
    ke_measured__knmm_rad: Optional[float]
    my_pos_100fit__knmm: Optional[float]
    my_neg_100fit__knmm: Optional[float]
    theta_p_pos_100fit__rad: Optional[float]
    theta_pc_pos_100fit__rad: Optional[float]
    theta_u_pos_100fit__rad: Optional[float]
    theta_p_neg_100fit__rad: Optional[float]
    theta_pc_neg_100fit__rad: Optional[float]
    theta_u_neg_100fit__rad: Optional[float]
    mc_my_pos_100fit: Optional[float]
    mu_mc_pos_100fit: Optional[float]
    mc_my_neg_100fit: Optional[float]
    mu_mc_neg_100fit: Optional[float]
    my_pos_80fit__knmm: Optional[float]
    my_neg_80fit__knmm: Optional[float]
    theta_p_pos_80fit__rad: Optional[float]
    theta_pc_pos_80fit__rad: Optional[float]
    theta_u_pos_80fit__rad: Optional[float]
    theta_p_neg_80fit__rad: Optional[float]
    theta_pc_neg_80fit__rad: Optional[float]
    theta_u_neg_80fit__rad: Optional[float]
    mc_my_pos_80fit: Optional[float]
    mu_mc_pos_80fit: Optional[float]
    mc_my_neg_80fit: Optional[float]
    mu_mc_neg_80fit: Optional[float]
    lambda_s: Optional[float]
    lambda_c: Optional[float]
    flexural_buckling: str
    latitude: Optional[float]
    longitude: Optional[float]
    # END_OF_GENERATED_CODE_hss_column

    moment_rotation_count: int


HSSColumnField = Enum(
    "HSSColumnField",
    {key: key for key in HSSColumnModel.model_fields},
    module=__name__,
    type=str,
)

HSSColumnNumberField = Enum(
    "HSSColumnNumberField",
    {
        key: key
        for key, field in HSSColumnModel.model_fields.items()
        if _field_base_type(field) in [Decimal, float, int]
    },
    module=__name__,
    type=str,
)


class EccentricBracedFrameModel(ApiModel):
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
    f_y_n_flg: float
    f_y_n_web: float
    f_u_n_flg: float
    f_u_n_web: float
    e_n_flg: int
    e_n_web: int
    f_y_m_flg: Optional[float]
    f_y_m_web: Optional[float]
    f_y_exp_l_flg: Optional[float]
    f_y_exp_l_web: Optional[float]
    f_u_m_flg: Optional[float]
    f_u_m_web: Optional[float]
    f_u_exp_l_flg: Optional[float]
    f_u_exp_l_web: Optional[float]
    e_m_flg: Optional[float]
    e_m_web: Optional[float]
    r_y_flg: Optional[float]
    r_y_web: Optional[float]
    r_t_flg: Optional[float]
    r_t_web: Optional[float]
    f_u_f_y_n_flg: Optional[float]
    f_u_f_y_n_web: Optional[float]
    f_u_f_y_m_flg: Optional[float]
    f_u_f_y_m_web: Optional[float]
    h_n: float
    tw_n: float
    bf_n: float
    tf_n: float
    tf_add_n: Optional[float]
    r_n: Optional[float]
    h_m: Optional[float]
    tw_m: Optional[float]
    bf_m: Optional[float]
    tf_m: Optional[float]
    tf_add_m: Optional[float]
    hw_n: float
    hw_m: Optional[float]
    a_fil_n: Optional[float]
    af_n: float
    aw_n: float
    a_n: float
    af_m: Optional[float]
    aw_m: Optional[float]
    a_m: Optional[float]
    zp_fil_n: Optional[float]
    zp_n: Optional[float]
    zp_no_fil_n: Optional[float]
    zp_fil_m: Optional[float]
    zp_m: Optional[float]
    zp_no_fil_m: Optional[float]
    link_loc: Optional[str]
    l_confi: Optional[str]
    l_con_typ: Optional[str]
    l_st: Optional[float]
    h_st: Optional[float]
    e: int
    l_con_confi: Optional[str]
    l_con_wld: Optional[str]
    l_endp_wld: Optional[str]
    l_bu_wld: Optional[str]
    l_s_side: Optional[str]
    l_s_reg: Optional[str]
    l_s_d_pnl_1_f: Optional[float]
    l_s_d_pnl_2_f: Optional[float]
    l_s_d_pnl_1_b: Optional[float]
    l_s_d_pnl_2_b: Optional[float]
    t_s: Optional[float]
    l_s_weld: Optional[str]
    l_s_no_f: Optional[int]
    l_s_no_b: Optional[int]
    a_b_b: Optional[float]
    t_e_s: Optional[float]
    t_b_s: Optional[float]
    d_b_s: Optional[float]
    d_b_pnl_1: Optional[float]
    d_b_pnl_2: Optional[float]
    b_s_no: Optional[int]
    l_p_typ: str
    n_d_n_pl_ten: Optional[float]
    n_d_n_pl_comp: Optional[float]
    fail_mode: Optional[str]
    ov_aisc: Optional[float]
    ov_ec8: Optional[float]
    class_aisc: str
    class_ec8: str
    reference: str
    url: str
    latitude: float
    longitude: float
    # END_OF_GENERATED_CODE_eccentric_braced_frame

    shear_link_angle_count: int


EccentricBracedFrameField = Enum(
    "EccentricBracedFrameField",
    {key: key for key in EccentricBracedFrameModel.model_fields},
    module=__name__,
    type=str,
)

EccentricBracedFrameNumberField = Enum(
    "EccentricBracedFrameNumberField",
    {
        key: key
        for key, field in EccentricBracedFrameModel.model_fields.items()
        if _field_base_type(field) in [Decimal, float, int]
    },
    module=__name__,
    type=str,
)


class TensileCouponModel(ApiModel):
    # START_OF_GENERATED_CODE_tensile_coupon
    experimental_program: str
    standard: str
    specimen_type: str
    id: str
    profile_type: str
    profile: str
    specimen_source: Optional[str]
    steel_grade: str
    avg_init_reduced_width__mm_: float
    avg_init_reduced_thickness__mm_: float
    avg_init_marked_gauge_length__mm_: float
    eff_fractured_width__mm_: float
    eff_fractured_thickness__mm_: float
    avg_fractured_marked_gauge_length__mm_: float
    fy_n__mpa_: float
    fu_n__mpa_: float
    t_a__deg_c_: float
    date: str
    year: int
    investigator: str
    location: str
    machine: str
    pid_force_p: Optional[float]
    pid_force_i: Optional[float]
    pid_force_d: Optional[float]
    pid_disp_p: Optional[float]
    pid_disp_i: Optional[float]
    pid_disp_d: Optional[float]
    pid_ext_p: Optional[float]
    pid_ext_i: Optional[float]
    pid_ext_d: Optional[float]
    yield_stress_02__mpa_: Optional[float]
    yield_strain_02: Optional[float]
    bin_discont_yield: bool
    yield_stress_uyp__mpa_: Optional[float]
    yield_stress_lyp__mpa_: Optional[float]
    yield_point_elongation: Optional[float]
    tensile_strength__mpa_: Optional[float]
    uniform_elongation: Optional[float]
    elongation_at_fracture: Optional[float]
    elongation_after_fracture: Optional[float]
    reduction_of_area: Optional[float]
    elastic_modulus__mpa_: Optional[float]
    c: Optional[float]
    si: Optional[float]
    mn: Optional[float]
    p: Optional[float]
    s: Optional[float]
    n: Optional[float]
    cu: Optional[float]
    mo: Optional[float]
    ni: Optional[float]
    cr: Optional[float]
    v: Optional[float]
    nb: Optional[float]
    ti: Optional[float]
    al: Optional[float]
    b: Optional[float]
    zr: Optional[float]
    sn: Optional[float]
    ca: Optional[float]
    h: Optional[float]
    fe: Optional[float]
    file_path: Optional[str]
    reference: Optional[str]
    link: Optional[str]
    latitude: float
    longitude: float
    publication_key: Optional[str]
    datacol_version: int
    # END_OF_GENERATED_CODE_tensile_coupon

    stress_strain_count: int


TensileCouponField = Enum(
    "TensileCouponField",
    {key: key for key in TensileCouponModel.model_fields},
    module=__name__,
    type=str,
)

TensileCouponNumberField = Enum(
    "TensileCouponNumberField",
    {
        key: key
        for key, field in TensileCouponModel.model_fields.items()
        if _field_base_type(field) in [Decimal, float, int]
    },
    module=__name__,
    type=str,
)


class DuctileFractureModel(ApiModel):
    # START_OF_GENERATED_CODE_ductile_fracture
    id: str
    specimen_designation: str
    experimental_program: str
    date: int
    specimen_type: str
    piece: str
    loading: str
    loading_protocol: str
    location_coupon: str
    section_type: str
    section_profile: str
    steel_type: str
    coupon_direction: str
    crack_opening_direction: str
    plate_thickness: float
    f_yn: float
    f_un: Optional[float]
    fy_m: Optional[float]
    fu_m: Optional[float]
    elongation_fr: Optional[float]
    temperature: float
    chemical_composition_C: Optional[float]
    chemical_composition_Si: Optional[float]
    chemical_composition_Mn: Optional[float]
    chemical_composition_P: Optional[float]
    chemical_composition_S: Optional[float]
    chemical_composition_Cu: Optional[float]
    chemical_composition_Ni: Optional[float]
    chemical_composition_Cr: Optional[float]
    chemical_composition_V: Optional[float]
    chemical_composition_Nb: Optional[float]
    chemical_composition_Mo: Optional[float]
    chemical_composition_Ti: Optional[float]
    chemical_composition_Al: Optional[float]
    chemical_composition_N: Optional[float]
    gauge_length: float
    nom_notch_radius: float
    nom_whole_diameter_cnt: Optional[float]
    nom_notch_diameter_cnt: Optional[float]
    nom_notch_width: float
    nom_width_gp: Optional[float]
    nom_whole_thickness_gp: Optional[float]
    nom_notch_thickness_gp: Optional[float]
    meas_whole_diameter_cnt: Optional[str]
    meas_notch_diameter_cnt: Optional[str]
    meas_notch_width: str
    meas_width_gp: Optional[str]
    meas_whole_thickness_gp: Optional[str]
    meas_notch_thickness_gp: Optional[str]
    disp_fract: Optional[float]
    exc_at_fract: Optional[int]
    step_fract: int
    fract_loc: str
    young_mod: float
    nu: float
    triax_at_fr: Optional[float]
    triax_avg_till_fr: float
    lode_at_fr: float
    lode_avg_till_fr: float
    peeq_at_fr: float
    cvgm_etamono: float
    cvgm_lambda: float
    swdfm_alpha_pos: float
    swdfm_alpha_neg: float
    swdfm_kappa: float
    swdfm_C: float
    swdfm_beta: float
    kk_alpha_1: float
    kk_alpha_2: float
    kk_beta_1: float
    kk_beta_2: float
    kk_d_cr: float
    l_star: Optional[float]
    reference: str
    link: str
    latitude: float
    longitude: float
    has_sem: Optional[bool]
    # END_OF_GENERATED_CODE_ductile_fracture

    force_elongation_count: int
    force_elongation_simulation_count: int
    force_radial_count: int
    force_radial_simulation_count: int
    epeq_simulation_count: int
    lode_simulation_count: int
    triax_simulation_count: int


DuctileFractureField = Enum(
    "DuctileFractureField",
    {key: key for key in DuctileFractureModel.model_fields},
    module=__name__,
    type=str,
)

DuctileFractureNumberField = Enum(
    "DuctileFractureNumberField",
    {
        key: key
        for key, field in DuctileFractureModel.model_fields.items()
        if _field_base_type(field) in [Decimal, float, int]
    },
    module=__name__,
    type=str,
)
