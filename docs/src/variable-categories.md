# Variable categories

Every database column belongs to one scientific category. The categories drive the
collapsible groups in the filter rail, the contribution editor, the curation review
panel and the specimen drawer, so a reader meets six to fourteen headings instead of
a flat list of up to 153 variables.

The categories are the ones the RESSLab researchers defined on
[resslab-hub#245](https://github.com/RESSLab-Team/resslab-hub/issues/245), and their
home is the `group` column of each `*_data_dictionary.csv`
([resslab-hub-data#46](https://github.com/RESSLab-Team/resslab-hub-data/pull/46)).
Connections, ductile fracture and residual stresses follow the grouping that a researcher of the lab made for them; the
other six follow the same conventions.

## How a column gets its category

1. If the data dictionary carries a `group` for the column, that wins.
2. Otherwise the per-database rules in `frontend/src/utils/fieldGroups.ts` decide,
   first match wins. They mirror the dictionaries, so the two agree.
3. Anything unclaimed lands in `other`, which `fieldGroups.spec.ts` asserts is always
   empty. It reads the real column list from `database-columns.json` at the repo
   root, which `make api` (and `make generate-model`) writes from the ORM models;
   a backend test fails when that file is stale. A column added to a data
   dictionary without a category fails the test suite (and CI) rather than
   quietly degrading the UI.

Rules prefer a pattern over a list of names wherever the naming already carries the
category, so `uvc_rho_new` joins the cyclic model parameters and `pid_torque_p` joins
the test equipment without anyone editing the taxonomy.

### Two traps worth knowing about

Element symbols collide with structural variables. `b` is boron in a coupon but the
section width in residual stresses, `h` is hydrogen or the section height, and `p` is
phosphorus or the applied axial load. The chemistry rules are listed per database,
never shared, and the test suite pins each case.

Ratios written with `_over_` are not one thing either: in the columns database
`h_over_t_cw` is a width-to-thickness ratio while `p_g_over_p_ym` is an axial load
ratio, and they belong in different groups.

### The review status

`data_curation_status` (#253) is in every database, in "Experimental program
details". The Hub sets it (`verified` or `unverified`, see
[curation.md](curation.md#verification)), so it is not in the filter rail
(`DENYLIST` in `utils/filterProfile.ts`, the "Verified only" toggle replaces it) nor
in the contribution editor. It still needs its category: the specimen drawer shows
it, and `fieldGroups.spec.ts` fails on a column with none.

## Connections, 154 columns in 14 groups

| Group | n | Columns |
|---|---:|---|
| Experimental program details | 11 | `id`, `experimental_program`, `date`, `specimen_designation`, `comments`, `loading_protocol`, `reference`, `link`, `latitude`, `longitude`, `data_curation_status` |
| Connection detailing | 7 | `northridge`, `specimen_type`, `slab`, `connection_type`, `t_pl`, `s_h`, `d_h` |
| Beam section properties | 24 | `rbs_cut`, `section_b`, `d_b`, `d_bg`, `t_bw`, `b_bf`, `t_bf`, `r_b`, `a_b`, `i_xb`, `z_xb`, `z_xb_bfp`, `r_yb`, `b_bf_rbs`, `d_gb_rbs`, `a_b_rbs`, `i_xb_rbs`, `z_xb_rbs`, `d_bm`, `d_bgm`, `t_bwm`, `b_bfm`, `t_bfm`, `z_xbm` |
| Beam material properties | 6 | `steel_b`, `f_yb`, `f_ybw`, `f_ybf`, `f_yb_mill`, `f_yb_avg` |
| Specimen dimensions | 5 | `l_b`, `l_fc`, `l_o`, `lo_db`, `h_c` |
| Column section properties | 14 | `section_c`, `d_c`, `t_cw`, `b_cf`, `c_c`, `t_cf`, `r_c`, `a_c`, `i_xc`, `d_cm`, `t_wcm`, `c_cm`, `b_fcm`, `t_fcm` |
| Column material properties | 7 | `steel_c`, `f_yc`, `f_ydp`, `f_ycw`, `f_ycf`, `f_yc_mill`, `f_yc_avg` |
| Weld details | 7 | `backing_bar`, `electrode`, `d_electrode`, `cvn_0f`, `cvn_minus20f`, `cvn_70f`, `access_hole_geometry` |
| Concrete slab properties | 22 | `w`, `w_l`, `w_r`, `h_t`, `a_s`, `f_sk`, `f_sm`, `h_co`, `slab_con_type`, `f_ck`, `f_cm`, `cur_days`, `f_c_compr_calc`, `d`, `h_sc`, `n_studs`, `n_diss`, `n_r`, `f_u_sc`, `h_p`, `b_o`, `deck_ribs_orientation` |
| Panel zone geometric properties | 19 | `section_shape_c`, `d_pz`, `tw_pz`, `bf_pz`, `tf_pz`, `dz`, `zw`, `dz_plug`, `wz_plug`, `wd`, `n_dp`, `t_dp`, `t_dp_tot`, `t_p`, `t_cp`, `d_cp`, `db_plus`, `db_minus`, `a_vc` |
| Panel zone resistance | 14 | `fy_pz_m`, `p_cm`, `n_pm`, `v_pz_el_m_europe`, `r_n_el_m_aisc`, `r_n_pl_m_aisc`, `v_pz_m_aij`, `fy_pz_n`, `p_cn`, `n_pn`, `v_pz_el_n_europe`, `r_n_el_n_aisc`, `r_n_pl_n_aisc`, `v_pz_n_aij` |
| Panel zone demand | 7 | `m_cf_minus_n`, `m_cf_plus_n`, `m_cf_minus_m`, `m_cf_plus_m`, `v_bf_plus_n`, `v_bf_minus_n`, `v_col_n` |
| Panel zone demand-to-resistance ratio | 8 | `r_u_n`, `r_u_m`, `ru_rn_el_n`, `ru_rn_pl_n`, `aisc_pz_violation_n`, `ru_rn_el_m`, `ru_rn_pl_m`, `aisc_pz_violation_m` |
| Panel zone shear distortion | 3 | `g_max`, `g_y`, `g_max_g_y` |

## Steel columns, 98 columns in 8 groups

| Group | n | Columns |
|---|---:|---|
| Experimental program details | 10 | `id`, `experimental_program`, `date`, `specimen_designation`, `comments`, `reference`, `link`, `latitude`, `longitude`, `data_curation_status` |
| Section properties | 20 | `section_c`, `d_c`, `k_c`, `k1_c`, `h_c`, `t_cw`, `b_cf`, `t_cf`, `a_cm`, `a_cn`, `i_xb`, `i_xc`, `s_xc`, `s_yc`, `z_xc`, `z_yc`, `j_c`, `c_wc`, `r_yc`, `r_xc` |
| Slenderness and section classification | 14 | `h_over_t_cw`, `b_f_over_t_cf`, `l_b_over_r_yc`, `k_xc`, `k_yc`, `lambda_xc`, `lambda_yc`, `lambda_ltb`, `f_class_us`, `w_class_us`, `cs_class_us`, `f_class_eu`, `w_class_eu`, `cs_class_eu` |
| Specimen dimensions | 5 | `l_c`, `l_sc`, `l_bc`, `t_top_plate`, `t_bottom_plate` |
| Material properties | 13 | `steel_c`, `r_y`, `r_t`, `f_ymf`, `f_ymw`, `f_umf`, `f_umw`, `f_yn`, `f_un`, `e_nc`, `e_mc`, `g_nc`, `g_mc` |
| Loading details | 14 | `boundary_condition`, `lateral_lp`, `direction_lp`, `axis_of_bending`, `axial_lp`, `p_g`, `p_g_over_p_ym`, `p_g_over_p_yn`, `p_t_over_p_ym`, `p_c_over_p_ym`, `p_c_over_p_yn`, `p`, `test_procedure`, `cfe` |
| Axial resistance | 5 | `p_ym`, `p_yn`, `p_ye`, `p_t`, `p_c` |
| Measured response | 17 | `k_test`, `k_flexure_th`, `k_shear_th`, `k_theory`, `th_y`, `th_lb`, `th_80`, `th_50`, `th_20`, `th_1l`, `th_2l`, `th_3l`, `th_4l`, `th_6l`, `d_80`, `d_50`, `d_20` |

## Steel braces, 72 columns in 10 groups

| Group | n | Columns |
|---|---:|---|
| Experimental program details | 9 | `id`, `investigator`, `specimen_ID`, `date`, `reference`, `link`, `latitude`, `longitude`, `data_curation_status` |
| Section properties | 14 | `cross_section_shape`, `cross_section_size`, `area`, `d_br`, `b_br`, `t_br`, `w_br`, `i_x`, `i_y`, `r_x`, `r_y`, `z_x`, `z_y`, `j` |
| Specimen details | 5 | `configuration`, `brace_angle`, `l_b`, `l_b_clear`, `boundary_condition` |
| Material properties | 5 | `steel`, `e`, `f_yn`, `fy_m`, `f_um` |
| Brace member geometric properties | 5 | `l_c`, `l_c_theory`, `k_assumed`, `kl_r`, `kl_r_theory` |
| Gusset plate dimensions | 18 | `l_1t`, `l_2t`, `l_3t`, `l_4t`, `l_5t`, `l_6t`, `l_7t`, `_8t`, `t_t`, `l_1b`, `l_2b`, `l_3b`, `l_4b`, `l_5b`, `l_6b`, `l_7b`, `l_8b`, `t_b` |
| Gusset plate material properties | 4 | `steel_gp`, `f_yn_gp`, `f_ym_gp`, `f_um_gp` |
| Connection detailing | 8 | `weld_type`, `l_weld`, `t_weld`, `stick_space`, `nub_bolts`, `bolt_size`, `bolt_mat`, `reinforcement_pl` |
| Loading details | 1 | `loading_protocol` |
| Measured and theoretical resistance | 3 | `p_t`, `p_t_theory`, `p_c` |

## HSS columns, 61 columns in 9 groups

| Group | n | Columns |
|---|---:|---|
| Experimental program details | 8 | `id`, `date`, `investigator`, `reference`, `url`, `latitude`, `longitude`, `data_curation_status` |
| Specimen details | 4 | `test_configuration`, `test_type`, `forming_process`, `seams` |
| Loading details | 5 | `loading_protocol`, `stiffness_coefficient`, `axial_load_ratio`, `axial_load_sequence`, `loading_angle` |
| Steel profile | 1 | `tube_section` |
| Section properties | 12 | `width__mm`, `depth__mm`, `flange_thickness__mm`, `web_thickness__mm`, `area__mm2`, `moment_of_inertia__mm4`, `radius__mm`, `depth_over_t`, `plastic_section_modulus__mm3`, `length__mm`, `lambda_s`, `lambda_c` |
| Material properties | 4 | `steel_type`, `fy_nominal__n_mm2`, `fy_measured__n_mm2`, `f_ultimate__n_mm2` |
| Measured response | 3 | `mp_measured__knmm`, `ke_measured__knmm_rad`, `flexural_buckling` |
| Backbone parameters (100% fit) | 12 | `my_pos_100fit__knmm`, `my_neg_100fit__knmm`, `theta_p_pos_100fit__rad`, `theta_pc_pos_100fit__rad`, `theta_u_pos_100fit__rad`, `theta_p_neg_100fit__rad`, `theta_pc_neg_100fit__rad`, `theta_u_neg_100fit__rad`, `mc_my_pos_100fit`, `mu_mc_pos_100fit`, `mc_my_neg_100fit`, `mu_mc_neg_100fit` |
| Backbone parameters (80% fit) | 12 | `my_pos_80fit__knmm`, `my_neg_80fit__knmm`, `theta_p_pos_80fit__rad`, `theta_pc_pos_80fit__rad`, `theta_u_pos_80fit__rad`, `theta_p_neg_80fit__rad`, `theta_pc_neg_80fit__rad`, `theta_u_neg_80fit__rad`, `mc_my_pos_80fit`, `mu_mc_pos_80fit`, `mc_my_neg_80fit`, `mu_mc_neg_80fit` |

## Eccentric braced frames, 99 columns in 9 groups

| Group | n | Columns |
|---|---:|---|
| Experimental program details | 10 | `id`, `investigator`, `year`, `spec_id`, `region`, `reference`, `url`, `latitude`, `longitude`, `data_curation_status` |
| Steel profile | 2 | `profile`, `sec_type` |
| Material properties | 26 | `sg_flg_link`, `sg_web_link`, `f_y_n_flg`, `f_y_n_web`, `f_u_n_flg`, `f_u_n_web`, `e_n_flg`, `e_n_web`, `f_y_m_flg`, `f_y_m_web`, `f_y_exp_l_flg`, `f_y_exp_l_web`, `f_u_m_flg`, `f_u_m_web`, `f_u_exp_l_flg`, `f_u_exp_l_web`, `e_m_flg`, `e_m_web`, `r_y_flg`, `r_y_web`, `r_t_flg`, `r_t_web`, `f_u_f_y_n_flg`, `f_u_f_y_n_web`, `f_u_f_y_m_flg`, `f_u_f_y_m_web` |
| Section properties | 26 | `h_n`, `tw_n`, `bf_n`, `tf_n`, `tf_add_n`, `r_n`, `h_m`, `tw_m`, `bf_m`, `tf_m`, `tf_add_m`, `hw_n`, `hw_m`, `a_fil_n`, `af_n`, `aw_n`, `a_n`, `af_m`, `aw_m`, `a_m`, `zp_fil_n`, `zp_n`, `zp_no_fil_n`, `zp_fil_m`, `zp_m`, `zp_no_fil_m` |
| Link details | 7 | `link_loc`, `l_confi`, `e`, `ov_aisc`, `ov_ec8`, `class_aisc`, `class_ec8` |
| Connection and weld details | 14 | `l_con_typ`, `l_st`, `h_st`, `l_con_confi`, `l_con_wld`, `l_endp_wld`, `l_bu_wld`, `a_b_b`, `t_e_s`, `t_b_s`, `d_b_s`, `d_b_pnl_1`, `d_b_pnl_2`, `b_s_no` |
| Stiffener details | 10 | `l_s_side`, `l_s_reg`, `l_s_d_pnl_1_f`, `l_s_d_pnl_2_f`, `l_s_d_pnl_1_b`, `l_s_d_pnl_2_b`, `t_s`, `l_s_weld`, `l_s_no_f`, `l_s_no_b` |
| Loading details | 3 | `l_p_typ`, `n_d_n_pl_ten`, `n_d_n_pl_comp` |
| Measured response | 1 | `fail_mode` |

## Cyclic coupons, 76 columns in 7 groups

| Group | n | Columns |
|---|---:|---|
| Experimental program details | 11 | `experimental_program`, `id`, `date`, `investigator`, `location`, `reference`, `link`, `latitude`, `longitude`, `citekey`, `data_curation_status` |
| Specimen details | 8 | `profile_type`, `profile`, `source`, `thickness`, `grade`, `spec`, `lp`, `size` |
| Geometric properties | 4 | `gage_length__mm_`, `avg_reduced_dia__mm_`, `avg_fractured_dia_top__mm_`, `avg_fractured_dia_bot__mm_` |
| Material properties | 6 | `fy_n__mpa_`, `fu_n__mpa_`, `t_a__deg_c_`, `yield_stress__mpa_`, `elastic_modulus__mpa_`, `fracture_strain` |
| Test equipment details | 10 | `machine`, `pid_force_k_p`, `pid_force_t_i`, `pid_force_t_d`, `pid_disp_k_p`, `pid_disp_t_i`, `pid_disp_t_d`, `pid_extenso_k_p`, `pid_extenso_t_i`, `pid_extenso_t_d` |
| Chemical composition | 20 | `c`, `si`, `mn`, `p`, `s`, `n`, `cu`, `mo`, `ni`, `cr`, `v`, `nb`, `ti`, `al`, `b`, `zr`, `sn`, `ca`, `h`, `fe` |
| Cyclic material model parameters | 17 | `uvc_phi__prct_`, `uvc_e__gpa_`, `uvc_sigma__mpa_`, `uvc_q__mpa_`, `uvc_b`, `uvc_d__mpa_`, `uvc_a`, `uvc_c1__mpa_`, `uvc_g1`, `uvc_c2__mpa_`, `uvc_g2`, `uvc_sigma_sat__mpa_`, `uvc_sigma_hard__mpa_`, `uvc_rho_yield`, `uvc_rho_iso`, `uvc_rho_kin`, `uvc_rho_d` |

## Tensile coupons, 71 columns in 7 groups

| Group | n | Columns |
|---|---:|---|
| Experimental program details | 14 | `experimental_program`, `id`, `date`, `year`, `investigator`, `location`, `file_path`, `reference`, `link`, `latitude`, `longitude`, `publication_key`, `datacol_version`, `data_curation_status` |
| Specimen details | 5 | `standard`, `specimen_type`, `profile_type`, `profile`, `specimen_source` |
| Material properties | 12 | `steel_grade`, `fy_n__mpa_`, `fu_n__mpa_`, `t_a__deg_c_`, `yield_stress_02__mpa_`, `yield_strain_02`, `bin_discont_yield`, `yield_stress_uyp__mpa_`, `yield_stress_lyp__mpa_`, `yield_point_elongation`, `tensile_strength__mpa_`, `elastic_modulus__mpa_` |
| Geometric properties | 6 | `avg_init_reduced_width__mm_`, `avg_init_reduced_thickness__mm_`, `avg_init_marked_gauge_length__mm_`, `eff_fractured_width__mm_`, `eff_fractured_thickness__mm_`, `avg_fractured_marked_gauge_length__mm_` |
| Test equipment details | 10 | `machine`, `pid_force_p`, `pid_force_i`, `pid_force_d`, `pid_disp_p`, `pid_disp_i`, `pid_disp_d`, `pid_ext_p`, `pid_ext_i`, `pid_ext_d` |
| Elongation and reduction of area | 4 | `uniform_elongation`, `elongation_at_fracture`, `elongation_after_fracture`, `reduction_of_area` |
| Chemical composition | 20 | `c`, `si`, `mn`, `p`, `s`, `n`, `cu`, `mo`, `ni`, `cr`, `v`, `nb`, `ti`, `al`, `b`, `zr`, `sn`, `ca`, `h`, `fe` |

## Ductile fracture, 79 columns in 8 groups

| Group | n | Columns |
|---|---:|---|
| Experimental program details | 11 | `id`, `specimen_designation`, `experimental_program`, `date`, `temperature`, `reference`, `link`, `latitude`, `longitude`, `has_sem`, `data_curation_status` |
| Specimen details | 7 | `specimen_type`, `piece`, `location_coupon`, `section_type`, `section_profile`, `crack_opening_direction`, `plate_thickness` |
| Loading details | 2 | `loading`, `loading_protocol` |
| Material properties | 9 | `steel_type`, `coupon_direction`, `f_yn`, `f_un`, `fy_m`, `fu_m`, `elongation_fr`, `young_mod`, `nu` |
| Chemical composition | 14 | `chemical_composition_C`, `chemical_composition_Si`, `chemical_composition_Mn`, `chemical_composition_P`, `chemical_composition_S`, `chemical_composition_Cu`, `chemical_composition_Ni`, `chemical_composition_Cr`, `chemical_composition_V`, `chemical_composition_Nb`, `chemical_composition_Mo`, `chemical_composition_Ti`, `chemical_composition_Al`, `chemical_composition_N` |
| Geometric properties | 14 | `gauge_length`, `nom_notch_radius`, `nom_whole_diameter_cnt`, `nom_notch_diameter_cnt`, `nom_notch_width`, `nom_width_gp`, `nom_whole_thickness_gp`, `nom_notch_thickness_gp`, `meas_whole_diameter_cnt`, `meas_notch_diameter_cnt`, `meas_notch_width`, `meas_width_gp`, `meas_whole_thickness_gp`, `meas_notch_thickness_gp` |
| Measured quantities at fracture | 9 | `disp_fract`, `exc_at_fract`, `step_fract`, `fract_loc`, `triax_at_fr`, `triax_avg_till_fr`, `lode_at_fr`, `lode_avg_till_fr`, `peeq_at_fr` |
| Fracture model parameters | 13 | `cvgm_etamono`, `cvgm_lambda`, `swdfm_alpha_pos`, `swdfm_alpha_neg`, `swdfm_kappa`, `swdfm_C`, `swdfm_beta`, `kk_alpha_1`, `kk_alpha_2`, `kk_beta_1`, `kk_beta_2`, `kk_d_cr`, `l_star` |

## Residual stresses, 49 columns in 7 groups

| Group | n | Columns |
|---|---:|---|
| Experimental program details | 10 | `id`, `experimental_program`, `date`, `spec_var`, `region`, `reference`, `link`, `latitude`, `longitude`, `data_curation_status` |
| Steel profile | 2 | `profile_type`, `profile` |
| Material properties | 8 | `steel`, `fy_n`, `fy_e`, `fy_mf`, `fy_mw`, `steel_web`, `fy_nw`, `fy_ew` |
| Section properties | 9 | `h`, `b`, `tw`, `tf`, `r`, `A`, `b2`, `tf2`, `sym` |
| Fabrication details | 13 | `plt_cut_f`, `plt_cut_w`, `weld_type`, `fillet_size`, `weld_cur`, `weld_vol`, `weld_vel`, `preheat_c`, `interpass_c`, `holding_c`, `holding_t`, `n_weld_pass`, `heat_inp` |
| Measured residual stresses | 6 | `sigma_0_f`, `sigma_0_w`, `flange_nr_data`, `mea_met`, `webdata`, `sigma_0_b_f` |
| Plot properties | 1 | `plot_sf` |

"Fabrication details" only applies to built-up (welded) sections. The specimen
drawer hides it on a hot-rolled record, where all its cells are empty.
