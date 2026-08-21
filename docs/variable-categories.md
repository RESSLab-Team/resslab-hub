# Variable categories

Every database column belongs to one scientific category. The categories drive the
collapsible groups in the filter rail, the contribution editor, the curation review
panel and the specimen drawer, so that a reader meets eight to twelve headings
instead of a flat list of up to 153 variables.

This document is the review surface for the domain calls. If a variable is in the
wrong group, that is a bug worth reporting: the grouping is what a reader navigates
by. The code is `frontend/src/utils/fieldGroups.ts` and the tables below were
generated from it against the real column list of each database.

## How a column gets its category

1. If the data dictionary carries a `category` for the column, that wins.
2. Otherwise the per-database rules in `fieldGroups.ts` decide, first match wins.
3. Anything unclaimed lands in `other`, which `fieldGroups.spec.ts` asserts is
   always empty. Adding a column to a data dictionary without a matching rule
   therefore fails the test suite rather than quietly degrading the UI.

Rules prefer a pattern over a list of names wherever the naming already carries the
category, so `uvc_rho_new` joins the model parameters and `pid_torque_p` joins the
instrumentation without anyone editing the taxonomy.

### One trap worth knowing about

Element symbols collide with structural variables. `b` is boron in a coupon and the
section width in residual stresses; `h` is hydrogen or the section height; `p` is
phosphorus or the applied axial load. The chemistry rule is therefore only reachable
from the three material databases, never applied globally, and the test suite pins
each of those three cases.

The same care applies to ratios written with `_over_`: in the columns database
`h_over_t_cw` is a width-to-thickness ratio while `p_g_over_p_ym` is an axial load
ratio, and they belong in different groups.

## The vocabulary

| Group | What it holds |
|---|---|
| `identification` | Which specimen this is: id, program, investigator, date, comments |
| `test_setup` | How the specimen was set up and what kind of test it was |
| `section` | The profile designation, how it was formed, where the coupon came from |
| `geometry` | Dimensions and derived section properties (nominal, where a split exists) |
| `geometry_measured` | The as-built counterparts of the above |
| `slenderness` | Width-to-thickness and slenderness ratios, and the section class they drive |
| `material` | Grade, yield and ultimate strength, elastic and shear modulus |
| `chemistry` | Chemical composition |
| `detailing` | What makes a connection this connection, rather than the members it joins |
| `welds` | Weld metal, electrode, toughness, weld access hole |
| `gusset_plate` | Both gusset plates of a brace and everything attaching the brace to them |
| `stiffeners` | Link stiffener layout and welding |
| `composite_slab` | Slab, deck, shear studs, concrete |
| `beam` | The beam of a connection: its geometry and its steel together |
| `column_member` | The column of a connection, likewise |
| `panel_zone` | Panel-zone geometry, doubler and continuity plates |
| `panel_zone_strength` | Panel-zone strength predicted by each code (Eurocode, AISC, AIJ) |
| `loading` | Loading protocol, applied loads, axial load ratio, temperature |
| `capacity` | Yield and buckling capacities, and demands normalised by them |
| `demand` | What the test actually demanded, and the resulting ratios |
| `response` | What was measured: stiffness, rotations, strengths, failure mode |
| `residual_stress` | The measured self-equilibrating stresses |
| `backbone_100fit` | IMK backbone calibrated on the full response |
| `backbone_80fit` | IMK backbone calibrated on the response truncated at 80 percent |
| `model_parameters` | Calibrated model parameters (UVC, CVGM, SWDFM, Kanvinde-Kiran) |
| `instrumentation` | Test frame and its PID gains |
| `imaging` | Availability of imaging (SEM) |
| `provenance` | Reference, link, coordinates, source file |
| `internal` | Bookkeeping the databases carry but a reader never needs |

## Connections, 153 columns in 12 groups

Split by entity rather than by aspect: a beam's dimensions and its steel belong
together in a reader's head, and the same for the column and the panel zone.

| Group | n | Columns |
|---|---:|---|
| `identification` | 5 | `id`, `experimental_program`, `date`, `specimen_designation`, `comments` |
| `test_setup` | 5 | `northridge`, `specimen_type`, `loading_protocol`, `slab`, `connection_type` |
| `detailing` | 4 | `t_pl`, `rbs_cut`, `s_h`, `d_h` |
| `beam` | 33 | `section_b`, `d_b`, `d_bg`, `t_bw`, `b_bf`, `t_bf`, `r_b`, `a_b`, `i_xb`, `z_xb`, `z_xb_bfp`, `r_yb`, `b_bf_rbs`, `d_gb_rbs`, `a_b_rbs`, `i_xb_rbs`, `z_xb_rbs`, `d_bm`, `d_bgm`, `t_bwm`, `b_bfm`, `t_bfm`, `z_xbm`, `steel_b`, `f_yb`, `f_ybw`, `f_ybf`, `f_yb_mill`, `f_yb_avg`, `l_b`, `l_fc`, `l_o`, `lo_db` |
| `column_member` | 23 | `section_c`, `d_c`, `t_cw`, `b_cf`, `c_c`, `t_cf`, `r_c`, `a_c`, `i_xc`, `d_cm`, `t_wcm`, `c_cm`, `b_fcm`, `t_fcm`, `steel_c`, `f_yc`, `f_ydp`, `f_ycw`, `f_ycf`, `f_yc_mill`, `f_yc_avg`, `h_c`, `section_shape_c` |
| `welds` | 11 | `backing_bar`, `electrode`, `d_electrode`, `cvn_0f`, `cvn_minus20f`, `cvn_70f`, `access_hole_geometry`, `w`, `w_l`, `w_r`, `h_t` |
| `composite_slab` | 18 | `a_s`, `f_sk`, `f_sm`, `h_co`, `slab_con_type`, `f_ck`, `f_cm`, `cur_days`, `f_c_compr_calc`, `d`, `h_sc`, `n_studs`, `n_diss`, `n_r`, `f_u_sc`, `h_p`, `b_o`, `deck_ribs_orientation` |
| `panel_zone` | 18 | `d_pz`, `tw_pz`, `bf_pz`, `tf_pz`, `dz`, `zw`, `dz_plug`, `wz_plug`, `wd`, `n_dp`, `t_dp`, `t_dp_tot`, `t_p`, `t_cp`, `d_cp`, `db_plus`, `db_minus`, `a_vc` |
| `panel_zone_strength` | 14 | `fy_pz_m`, `p_cm`, `n_pm`, `v_pz_el_m_europe`, `r_n_el_m_aisc`, `r_n_pl_m_aisc`, `v_pz_m_aij`, `fy_pz_n`, `p_cn`, `n_pn`, `v_pz_el_n_europe`, `r_n_el_n_aisc`, `r_n_pl_n_aisc`, `v_pz_n_aij` |
| `demand` | 15 | `m_cf_minus_n`, `m_cf_plus_n`, `m_cf_minus_m`, `m_cf_plus_m`, `v_bf_plus_n`, `v_bf_minus_n`, `v_col_n`, `r_u_n`, `r_u_m`, `ru_rn_el_n`, `ru_rn_pl_n`, `aisc_pz_violation_n`, `ru_rn_el_m`, `ru_rn_pl_m`, `aisc_pz_violation_m` |
| `response` | 3 | `g_max`, `g_y`, `g_max_g_y` |
| `provenance` | 4 | `reference`, `link`, `latitude`, `longitude` |

The panel zone is split in two because its geometry and its code-predicted strength
run to 32 columns together, more than any other single subject in the schema.

## Steel columns, 97 columns in 8 groups

| Group | n | Columns |
|---|---:|---|
| `identification` | 5 | `id`, `experimental_program`, `date`, `specimen_designation`, `comments` |
| `geometry` | 25 | `section_c`, `d_c`, `k_c`, `k1_c`, `h_c`, `t_cw`, `b_cf`, `t_cf`, `a_cm`, `a_cn`, `i_xb`, `i_xc`, `s_xc`, `s_yc`, `z_xc`, `z_yc`, `j_c`, `c_wc`, `r_yc`, `r_xc`, `l_c`, `l_sc`, `l_bc`, `t_top_plate`, `t_bottom_plate` |
| `slenderness` | 14 | `h_over_t_cw`, `b_f_over_t_cf`, `l_b_over_r_yc`, `k_xc`, `k_yc`, `lambda_xc`, `lambda_yc`, `lambda_ltb`, `f_class_us`, `w_class_us`, `cs_class_us`, `f_class_eu`, `w_class_eu`, `cs_class_eu` |
| `material` | 13 | `steel_c`, `r_y`, `r_t`, `f_ymf`, `f_ymw`, `f_umf`, `f_umw`, `f_yn`, `f_un`, `e_nc`, `e_mc`, `g_nc`, `g_mc` |
| `loading` | 11 | `boundary_condition`, `lateral_lp`, `direction_lp`, `axis_of_bending`, `axial_lp`, `p_g`, `p_g_over_p_ym`, `p_g_over_p_yn`, `p`, `test_procedure`, `cfe` |
| `capacity` | 8 | `p_ym`, `p_yn`, `p_ye`, `p_t`, `p_c`, `p_t_over_p_ym`, `p_c_over_p_ym`, `p_c_over_p_yn` |
| `response` | 17 | `k_test`, `k_flexure_th`, `k_shear_th`, `k_theory`, `th_y`, `th_lb`, `th_80`, `th_50`, `th_20`, `th_1l`, `th_2l`, `th_3l`, `th_4l`, `th_6l`, `d_80`, `d_50`, `d_20` |
| `provenance` | 4 | `reference`, `link`, `latitude`, `longitude` |

The applied gravity load and its ratios sit under loading, not capacity: the axial
load ratio is what a reader is after when they ask how a column was tested. The
yield and buckling capacities, and the demands normalised by them, stay under
capacity.

## Steel braces, 71 columns in 8 groups

| Group | n | Columns |
|---|---:|---|
| `identification` | 4 | `id`, `investigator`, `specimen_ID`, `date` |
| `geometry` | 14 | `cross_section_shape`, `cross_section_size`, `area`, `d_br`, `b_br`, `t_br`, `w_br`, `i_x`, `i_y`, `r_x`, `r_y`, `z_x`, `z_y`, `j` |
| `test_setup` | 5 | `configuration`, `brace_angle`, `l_b`, `l_b_clear`, `boundary_condition` |
| `material` | 5 | `steel`, `e`, `f_yn`, `fy_m`, `f_um` |
| `gusset_plate` | 30 | `l_1t`, `l_2t`, `l_3t`, `l_4t`, `l_5t`, `l_6t`, `l_7t`, `_8t`, `t_t`, `l_1b`, `l_2b`, `l_3b`, `l_4b`, `l_5b`, `l_6b`, `l_7b`, `l_8b`, `t_b`, `steel_gp`, `f_yn_gp`, `f_ym_gp`, `f_um_gp`, `weld_type`, `l_weld`, `t_weld`, `stick_space`, `nub_bolts`, `bolt_size`, `bolt_mat`, `reinforcement_pl` |
| `loading` | 1 | `loading_protocol` |
| `capacity` | 8 | `p_t`, `p_t_theory`, `p_c`, `kl_r`, `l_c`, `l_c_theory`, `k_assumed`, `kl_r_theory` |
| `provenance` | 4 | `reference`, `link`, `latitude`, `longitude` |

`_8t` really is spelled with a leading underscore in the data dictionary, between
`l_7t` and `t_t`. It is grouped with its siblings rather than treated as a typo.

## HSS columns, 60 columns in 11 groups

| Group | n | Columns |
|---|---:|---|
| `identification` | 3 | `id`, `date`, `investigator` |
| `test_setup` | 4 | `test_configuration`, `stiffness_coefficient`, `test_type`, `flexural_buckling` |
| `loading` | 4 | `loading_protocol`, `axial_load_ratio`, `axial_load_sequence`, `loading_angle` |
| `section` | 3 | `forming_process`, `seams`, `tube_section` |
| `geometry` | 9 | `width__mm`, `depth__mm`, `flange_thickness__mm`, `web_thickness__mm`, `area__mm2`, `moment_of_inertia__mm4`, `radius__mm`, `plastic_section_modulus__mm3`, `length__mm` |
| `slenderness` | 3 | `depth_over_t`, `lambda_s`, `lambda_c` |
| `material` | 4 | `steel_type`, `fy_nominal__n_mm2`, `fy_measured__n_mm2`, `f_ultimate__n_mm2` |
| `capacity` | 2 | `mp_measured__knmm`, `ke_measured__knmm_rad` |
| `backbone_100fit` | 12 | `my_pos_100fit__knmm`, `my_neg_100fit__knmm`, `theta_p_pos_100fit__rad`, `theta_pc_pos_100fit__rad`, `theta_u_pos_100fit__rad`, `theta_p_neg_100fit__rad`, `theta_pc_neg_100fit__rad`, `theta_u_neg_100fit__rad`, `mc_my_pos_100fit`, `mu_mc_pos_100fit`, `mc_my_neg_100fit`, `mu_mc_neg_100fit` |
| `backbone_80fit` | 12 | `my_pos_80fit__knmm`, `my_neg_80fit__knmm`, `theta_p_pos_80fit__rad`, `theta_pc_pos_80fit__rad`, `theta_u_pos_80fit__rad`, `theta_p_neg_80fit__rad`, `theta_pc_neg_80fit__rad`, `theta_u_neg_80fit__rad`, `mc_my_pos_80fit`, `mu_mc_pos_80fit`, `mc_my_neg_80fit`, `mu_mc_neg_80fit` |
| `provenance` | 4 | `reference`, `url`, `latitude`, `longitude` |

The two backbone calibrations stay apart. Mixing them would put twenty-four columns
with near-identical names in one list, which is precisely the confusion the
grouping exists to remove.

## Eccentric braced frames, 98 columns in 10 groups

| Group | n | Columns |
|---|---:|---|
| `identification` | 5 | `id`, `investigator`, `year`, `spec_id`, `region` |
| `section` | 9 | `profile`, `sec_type`, `link_loc`, `l_confi`, `e`, `ov_aisc`, `ov_ec8`, `class_aisc`, `class_ec8` |
| `material` | 26 | `sg_flg_link`, `sg_web_link`, `f_y_n_flg`, `f_y_n_web`, `f_u_n_flg`, `f_u_n_web`, `e_n_flg`, `e_n_web`, `f_y_m_flg`, `f_y_m_web`, `f_y_exp_l_flg`, `f_y_exp_l_web`, `f_u_m_flg`, `f_u_m_web`, `f_u_exp_l_flg`, `f_u_exp_l_web`, `e_m_flg`, `e_m_web`, `r_y_flg`, `r_y_web`, `r_t_flg`, `r_t_web`, `f_u_f_y_n_flg`, `f_u_f_y_n_web`, `f_u_f_y_m_flg`, `f_u_f_y_m_web` |
| `geometry` | 14 | `h_n`, `tw_n`, `bf_n`, `tf_n`, `tf_add_n`, `r_n`, `hw_n`, `a_fil_n`, `af_n`, `aw_n`, `a_n`, `zp_fil_n`, `zp_n`, `zp_no_fil_n` |
| `geometry_measured` | 12 | `h_m`, `tw_m`, `bf_m`, `tf_m`, `tf_add_m`, `hw_m`, `af_m`, `aw_m`, `a_m`, `zp_fil_m`, `zp_m`, `zp_no_fil_m` |
| `stiffeners` | 10 | `l_s_side`, `l_s_reg`, `l_s_d_pnl_1_f`, `l_s_d_pnl_2_f`, `l_s_d_pnl_1_b`, `l_s_d_pnl_2_b`, `t_s`, `l_s_weld`, `l_s_no_f`, `l_s_no_b` |
| `welds` | 14 | `l_con_typ`, `l_st`, `h_st`, `l_con_confi`, `l_con_wld`, `l_endp_wld`, `l_bu_wld`, `a_b_b`, `t_e_s`, `t_b_s`, `d_b_s`, `d_b_pnl_1`, `d_b_pnl_2`, `b_s_no` |
| `loading` | 3 | `l_p_typ`, `n_d_n_pl_ten`, `n_d_n_pl_comp` |
| `response` | 1 | `fail_mode` |
| `provenance` | 4 | `reference`, `url`, `latitude`, `longitude` |

Nominal and measured geometry are separate groups because EBF reports both for
almost every dimension, and a reader is nearly always after one or the other.

## Cyclic coupons, 78 columns in 9 groups

| Group | n | Columns |
|---|---:|---|
| `identification` | 5 | `experimental_program`, `id`, `date`, `investigator`, `location` |
| `section` | 8 | `profile_type`, `profile`, `source`, `thickness`, `grade`, `spec`, `lp`, `size` |
| `geometry` | 4 | `gage_length__mm_`, `avg_reduced_dia__mm_`, `avg_fractured_dia_top__mm_`, `avg_fractured_dia_bot__mm_` |
| `material` | 6 | `fy_n__mpa_`, `fu_n__mpa_`, `t_a__deg_c_`, `yield_stress__mpa_`, `elastic_modulus__mpa_`, `fracture_strain` |
| `chemistry` | 20 | `c`, `si`, `mn`, `p`, `s`, `n`, `cu`, `mo`, `ni`, `cr`, `v`, `nb`, `ti`, `al`, `b`, `zr`, `sn`, `ca`, `h`, `fe` |
| `instrumentation` | 10 | `machine`, `pid_force_k_p`, `pid_force_t_i`, `pid_force_t_d`, `pid_disp_k_p`, `pid_disp_t_i`, `pid_disp_t_d`, `pid_extenso_k_p`, `pid_extenso_t_i`, `pid_extenso_t_d` |
| `model_parameters` | 17 | `uvc_phi__prct_`, `uvc_e__mpa_`, `uvc_sigma__mpa_`, `uvc_q__mpa_`, `uvc_b`, `uvc_d__mpa_`, `uvc_a`, `uvc_c1__mpa_`, `uvc_g1`, `uvc_c2__mpa_`, `uvc_g2`, `uvc_sigma_sat__mpa_`, `uvc_sigma_hard__mpa_`, `uvc_rho_yield`, `uvc_rho_iso`, `uvc_rho_kin`, `uvc_rho_d` |
| `provenance` | 6 | `file`, `reference`, `link`, `latitude`, `longitude`, `citekey` |
| `internal` | 2 | `hidden_index`, `hidden_dataset_index` |

## Tensile coupons, 70 columns in 9 groups

| Group | n | Columns |
|---|---:|---|
| `identification` | 6 | `experimental_program`, `id`, `date`, `year`, `investigator`, `location` |
| `section` | 5 | `standard`, `specimen_type`, `profile_type`, `profile`, `specimen_source` |
| `geometry` | 6 | `avg_init_reduced_width__mm_`, `avg_init_reduced_thickness__mm_`, `avg_init_marked_gauge_length__mm_`, `eff_fractured_width__mm_`, `eff_fractured_thickness__mm_`, `avg_fractured_marked_gauge_length__mm_` |
| `material` | 4 | `steel_grade`, `fy_n__mpa_`, `fu_n__mpa_`, `t_a__deg_c_` |
| `response` | 12 | `yield_stress_02__mpa_`, `yield_strain_02`, `bin_discont_yield`, `yield_stress_uyp__mpa_`, `yield_stress_lyp__mpa_`, `yield_point_elongation`, `tensile_strength__mpa_`, `uniform_elongation`, `elongation_at_fracture`, `elongation_after_fracture`, `reduction_of_area`, `elastic_modulus__mpa_` |
| `chemistry` | 20 | `c`, `si`, `mn`, `p`, `s`, `n`, `cu`, `mo`, `ni`, `cr`, `v`, `nb`, `ti`, `al`, `b`, `zr`, `sn`, `ca`, `h`, `fe` |
| `instrumentation` | 10 | `machine`, `pid_force_p`, `pid_force_i`, `pid_force_d`, `pid_disp_p`, `pid_disp_i`, `pid_disp_d`, `pid_ext_p`, `pid_ext_i`, `pid_ext_d` |
| `provenance` | 6 | `file_path`, `reference`, `link`, `latitude`, `longitude`, `publication_key` |
| `internal` | 1 | `datacol_version` |

The nominal grade sits under material and everything read off the measured
stress-strain curve sits under response, which keeps the reported strength apart
from the specified one.

## Ductile fracture, 78 columns in 11 groups

| Group | n | Columns |
|---|---:|---|
| `identification` | 4 | `id`, `specimen_designation`, `experimental_program`, `date` |
| `section` | 8 | `specimen_type`, `piece`, `location_coupon`, `section_type`, `section_profile`, `coupon_direction`, `crack_opening_direction`, `plate_thickness` |
| `loading` | 3 | `loading`, `loading_protocol`, `temperature` |
| `material` | 8 | `steel_type`, `f_yn`, `f_un`, `fy_m`, `fu_m`, `elongation_fr`, `young_mod`, `nu` |
| `chemistry` | 14 | `chemical_composition_C`, `chemical_composition_Si`, `chemical_composition_Mn`, `chemical_composition_P`, `chemical_composition_S`, `chemical_composition_Cu`, `chemical_composition_Ni`, `chemical_composition_Cr`, `chemical_composition_V`, `chemical_composition_Nb`, `chemical_composition_Mo`, `chemical_composition_Ti`, `chemical_composition_Al`, `chemical_composition_N` |
| `geometry` | 8 | `gauge_length`, `nom_notch_radius`, `nom_whole_diameter_cnt`, `nom_notch_diameter_cnt`, `nom_notch_width`, `nom_width_gp`, `nom_whole_thickness_gp`, `nom_notch_thickness_gp` |
| `geometry_measured` | 6 | `meas_whole_diameter_cnt`, `meas_notch_diameter_cnt`, `meas_notch_width`, `meas_width_gp`, `meas_whole_thickness_gp`, `meas_notch_thickness_gp` |
| `response` | 10 | `disp_fract`, `exc_at_fract`, `step_fract`, `fract_loc`, `triax_at_fr`, `triax_avg_till_fr`, `lode_at_fr`, `lode_avg_till_fr`, `peeq_at_fr`, `l_star` |
| `model_parameters` | 12 | `cvgm_etamono`, `cvgm_lambda`, `swdfm_alpha_pos`, `swdfm_alpha_neg`, `swdfm_kappa`, `swdfm_C`, `swdfm_beta`, `kk_alpha_1`, `kk_alpha_2`, `kk_beta_1`, `kk_beta_2`, `kk_d_cr` |
| `imaging` | 1 | `has_sem` |
| `provenance` | 4 | `reference`, `link`, `latitude`, `longitude` |

Stress triaxiality, Lode parameter and equivalent plastic strain at fracture are
measurements, so they sit under response. The three calibrated fracture models
(cyclic void growth, stress-weighted damage, Kanvinde-Kiran) sit together under
model parameters.

## Residual stresses, 25 columns in 6 groups

| Group | n | Columns |
|---|---:|---|
| `identification` | 3 | `id`, `experimental_program`, `date` |
| `geometry` | 9 | `profile_type`, `profile`, `spec_var`, `h`, `b`, `tw`, `tf`, `r`, `A` |
| `material` | 5 | `steel`, `fy_n`, `fy_e`, `fy_mf`, `fy_mw` |
| `residual_stress` | 2 | `sigma_0_f`, `sigma_0_w` |
| `provenance` | 4 | `reference`, `link`, `latitude`, `longitude` |
| `internal` | 2 | `flange_nr_data`, `plot_sf` |

## Moving the taxonomy into the data dictionary

The categories live in the frontend today so the UI could improve without a data
migration, but the right long-term owner is the data dictionary itself, next to the
description, symbol and unit that researchers already maintain. `groupFor()` already
prefers a `category` carried by `DictColumn`, so the migration needs no frontend
rework. What it touches:

- a tenth column in every `*_data_dictionary.csv` in `resslab-hub-data`
- `backend/resslab_hub/data/uploader.py`, `DictionaryUploader.upload_one`, which
  parses the seven-column header today
- `backend/resslab_hub/models/database/dictionary.py` and an Alembic revision
- `DictionaryColumnModel` in `backend/resslab_hub/models/api.py`
- `buildDictionaryCsv` in `frontend/src/utils/templates.ts`, so a downloaded
  dictionary round-trips

Until then the rules in `fieldGroups.ts` are the source of truth, and the coverage
test is what keeps them honest.
