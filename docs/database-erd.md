# Database ERD

Every table on `Base.metadata` (`backend/resslab_hub/models/database/`), generated
with `cd backend && make erd`. Regenerate after a migration changes the schema.

```mermaid
erDiagram
  auth_identity {
    DATETIME created_at
    VARCHAR handle
    UUID id PK
    DATETIME last_used_at
    VARCHAR provider
    VARCHAR subject
    UUID user_id FK
  }
  auth_login_challenge {
    INTEGER attempts
    VARCHAR code_hash
    DATETIME consumed_at
    DATETIME created_at
    VARCHAR email
    DATETIME expires_at
    UUID id PK
    VARCHAR ip
    VARCHAR kind
    UUID link_user_id FK
    VARCHAR redirect_to
    VARCHAR token_hash "indexed"
  }
  auth_session {
    DATETIME created_at
    DATETIME expires_at "indexed"
    UUID id PK
    VARCHAR ip
    DATETIME last_seen_at
    VARCHAR provider
    DATETIME revoked_at
    VARCHAR token_hash
    VARCHAR user_agent
    UUID user_id FK
  }
  auth_user {
    TEXT address
    DATETIME created_at
    DATETIME disabled_at
    VARCHAR display_name
    VARCHAR email
    DATETIME email_verified_at
    VARCHAR github_login
    VARCHAR github_role
    DATETIME github_role_synced_at
    UUID id PK
    VARCHAR institution
    DATETIME last_login_at
    VARCHAR orcid
    VARCHAR role
    VARCHAR role_override
    VARCHAR role_source
  }
  brace {
    FLOAT _8t
    FLOAT area
    FLOAT b_br
    VARCHAR bolt_mat
    VARCHAR bolt_size
    VARCHAR boundary_condition
    FLOAT brace_angle
    VARCHAR configuration
    VARCHAR cross_section_shape
    VARCHAR cross_section_size
    FLOAT d_br
    SMALLINT date
    SMALLINT displacement_count
    FLOAT e
    FLOAT f_um
    FLOAT f_um_gp
    FLOAT f_ym_gp
    FLOAT f_yn
    FLOAT f_yn_gp
    FLOAT fy_m
    FLOAT i_x
    FLOAT i_y
    VARCHAR id PK
    VARCHAR investigator
    FLOAT j
    FLOAT k_assumed
    FLOAT kl_r
    FLOAT kl_r_theory
    VARCHAR l_1b
    VARCHAR l_1t
    VARCHAR l_2b
    VARCHAR l_2t
    VARCHAR l_3b
    VARCHAR l_3t
    VARCHAR l_4b
    FLOAT l_4t
    VARCHAR l_5b
    VARCHAR l_5t
    VARCHAR l_6b
    VARCHAR l_6t
    FLOAT l_7b
    VARCHAR l_7t
    FLOAT l_8b
    FLOAT l_b
    FLOAT l_b_clear
    FLOAT l_c
    FLOAT l_c_theory
    FLOAT l_weld
    NUMERIC latitude
    VARCHAR link
    VARCHAR loading_protocol
    NUMERIC longitude
    FLOAT nub_bolts
    FLOAT p_c
    FLOAT p_t
    FLOAT p_t_theory
    FLOAT r_x
    FLOAT r_y
    VARCHAR reference
    VARCHAR reinforcement_pl
    VARCHAR specimen_ID
    VARCHAR steel
    VARCHAR steel_gp
    FLOAT stick_space
    VARCHAR t_b
    FLOAT t_br
    FLOAT t_t
    FLOAT t_weld
    FLOAT w_br
    VARCHAR weld_type
    FLOAT z_x
    FLOAT z_y
  }
  brace_displacement {
    VARCHAR brace_id PK
    NUMERIC displacement
    NUMERIC force
    BIGINT id PK
  }
  column {
    FLOAT a_cm
    FLOAT a_cn
    VARCHAR axial_lp
    SMALLINT axial_shortening_count
    VARCHAR axis_of_bending
    FLOAT b_cf
    FLOAT b_f_over_t_cf
    VARCHAR boundary_condition
    FLOAT c_wc
    BOOLEAN cfe
    VARCHAR comments
    VARCHAR cs_class_eu
    VARCHAR cs_class_us
    FLOAT d_20
    FLOAT d_50
    FLOAT d_80
    FLOAT d_c
    SMALLINT date
    VARCHAR direction_lp
    FLOAT e_mc
    FLOAT e_nc
    VARCHAR experimental_program
    VARCHAR f_class_eu
    VARCHAR f_class_us
    FLOAT f_umf
    FLOAT f_umw
    FLOAT f_un
    FLOAT f_ymf
    FLOAT f_ymw
    FLOAT f_yn
    FLOAT g_mc
    FLOAT g_nc
    FLOAT h_c
    FLOAT h_over_t_cw
    FLOAT i_xb
    FLOAT i_xc
    VARCHAR id PK
    FLOAT j_c
    FLOAT k1_c
    FLOAT k_c
    FLOAT k_flexure_th
    FLOAT k_shear_th
    FLOAT k_test
    FLOAT k_theory
    FLOAT k_xc
    FLOAT k_yc
    FLOAT l_b_over_r_yc
    FLOAT l_bc
    FLOAT l_c
    FLOAT l_sc
    FLOAT lambda_ltb
    FLOAT lambda_xc
    FLOAT lambda_yc
    VARCHAR lateral_lp
    FLOAT latitude
    VARCHAR link
    FLOAT longitude
    SMALLINT moment_strong_count
    SMALLINT moment_weak_count
    FLOAT p
    FLOAT p_c
    FLOAT p_c_over_p_ym
    FLOAT p_c_over_p_yn
    FLOAT p_g
    FLOAT p_g_over_p_ym
    FLOAT p_g_over_p_yn
    FLOAT p_t
    FLOAT p_t_over_p_ym
    FLOAT p_ye
    FLOAT p_ym
    FLOAT p_yn
    FLOAT r_t
    FLOAT r_xc
    FLOAT r_y
    FLOAT r_yc
    VARCHAR reference
    FLOAT s_xc
    FLOAT s_yc
    VARCHAR section_c
    VARCHAR specimen_designation
    VARCHAR steel_c
    FLOAT t_bottom_plate
    FLOAT t_cf
    FLOAT t_cw
    FLOAT t_top_plate
    VARCHAR test_procedure
    FLOAT th_1l
    FLOAT th_20
    FLOAT th_2l
    FLOAT th_3l
    FLOAT th_4l
    FLOAT th_50
    FLOAT th_6l
    FLOAT th_80
    FLOAT th_lb
    FLOAT th_y
    VARCHAR w_class_eu
    VARCHAR w_class_us
    FLOAT z_xc
    FLOAT z_yc
  }
  column_axial_shortening {
    NUMERIC axial_shortening
    NUMERIC chord_rotation
    VARCHAR column_id PK
    BIGINT id PK
  }
  column_moment_strong {
    NUMERIC chord_rotation
    VARCHAR column_id PK
    BIGINT id PK
    NUMERIC moment
  }
  column_moment_weak {
    NUMERIC chord_rotation
    VARCHAR column_id PK
    BIGINT id PK
    NUMERIC moment
  }
  connection {
    FLOAT a_b
    FLOAT a_b_rbs
    FLOAT a_c
    FLOAT a_s
    FLOAT a_vc
    VARCHAR access_hole_geometry
    BOOLEAN aisc_pz_violation_m
    BOOLEAN aisc_pz_violation_n
    FLOAT b_bf
    FLOAT b_bf_rbs
    FLOAT b_bfm
    FLOAT b_cf
    FLOAT b_fcm
    FLOAT b_o
    BOOLEAN backing_bar
    SMALLINT beam_count
    SMALLINT beam_west_count
    FLOAT bf_pz
    FLOAT c_c
    FLOAT c_cm
    VARCHAR comments
    VARCHAR connection_type
    VARCHAR cur_days
    FLOAT cvn_0f
    FLOAT cvn_70f
    FLOAT cvn_minus20f
    FLOAT d
    FLOAT d_b
    FLOAT d_bg
    FLOAT d_bgm
    FLOAT d_bm
    FLOAT d_c
    FLOAT d_cm
    FLOAT d_cp
    FLOAT d_electrode
    FLOAT d_gb_rbs
    FLOAT d_h
    FLOAT d_pz
    SMALLINT date
    FLOAT db_minus
    FLOAT db_plus
    VARCHAR deck_ribs_orientation
    FLOAT dz
    FLOAT dz_plug
    VARCHAR electrode
    VARCHAR experimental_program
    FLOAT f_c_compr_calc
    FLOAT f_ck
    FLOAT f_cm
    FLOAT f_sk
    FLOAT f_sm
    FLOAT f_u_sc
    FLOAT f_yb
    FLOAT f_yb_avg
    FLOAT f_yb_mill
    FLOAT f_ybf
    FLOAT f_ybw
    FLOAT f_yc
    FLOAT f_yc_avg
    FLOAT f_yc_mill
    FLOAT f_ycf
    FLOAT f_ycw
    FLOAT f_ydp
    FLOAT fy_pz_m
    FLOAT fy_pz_n
    FLOAT g_max
    FLOAT g_max_g_y
    FLOAT g_y
    SMALLINT global_count
    SMALLINT global_west_count
    FLOAT h_c
    FLOAT h_co
    FLOAT h_p
    FLOAT h_sc
    FLOAT h_t
    FLOAT i_xb
    FLOAT i_xb_rbs
    FLOAT i_xc
    VARCHAR id PK
    FLOAT l_b
    FLOAT l_fc
    FLOAT l_o
    FLOAT latitude
    VARCHAR link
    FLOAT lo_db
    VARCHAR loading_protocol
    FLOAT longitude
    FLOAT m_cf_minus_m
    FLOAT m_cf_minus_n
    FLOAT m_cf_plus_m
    FLOAT m_cf_plus_n
    SMALLINT n_diss
    SMALLINT n_dp
    FLOAT n_pm
    FLOAT n_pn
    SMALLINT n_r
    SMALLINT n_studs
    VARCHAR northridge
    FLOAT p_cm
    FLOAT p_cn
    SMALLINT panel_zone_count
    FLOAT r_b
    FLOAT r_c
    FLOAT r_n_el_m_aisc
    FLOAT r_n_el_n_aisc
    FLOAT r_n_pl_m_aisc
    FLOAT r_n_pl_n_aisc
    FLOAT r_u_m
    FLOAT r_u_n
    FLOAT r_yb
    FLOAT rbs_cut
    VARCHAR reference
    FLOAT ru_rn_el_m
    FLOAT ru_rn_el_n
    FLOAT ru_rn_pl_m
    FLOAT ru_rn_pl_n
    FLOAT s_h
    VARCHAR section_b
    VARCHAR section_c
    VARCHAR section_shape_c
    BOOLEAN slab
    VARCHAR slab_con_type
    VARCHAR specimen_designation
    VARCHAR specimen_type
    VARCHAR steel_b
    VARCHAR steel_c
    FLOAT t_bf
    FLOAT t_bfm
    FLOAT t_bw
    FLOAT t_bwm
    FLOAT t_cf
    FLOAT t_cp
    FLOAT t_cw
    FLOAT t_dp
    FLOAT t_dp_tot
    FLOAT t_fcm
    FLOAT t_p
    FLOAT t_pl
    FLOAT t_wcm
    FLOAT tf_pz
    FLOAT tw_pz
    FLOAT v_bf_minus_n
    FLOAT v_bf_plus_n
    FLOAT v_col_n
    FLOAT v_pz_el_m_europe
    FLOAT v_pz_el_n_europe
    FLOAT v_pz_m_aij
    FLOAT v_pz_n_aij
    FLOAT w
    FLOAT w_l
    FLOAT w_r
    FLOAT wd
    FLOAT wz_plug
    FLOAT z_xb
    FLOAT z_xb_bfp
    FLOAT z_xb_rbs
    FLOAT z_xbm
    FLOAT zw
  }
  connection_beam {
    NUMERIC chord_rotation
    VARCHAR connection_id PK
    BIGINT id PK
    NUMERIC moment
  }
  connection_beam_west {
    NUMERIC chord_rotation
    VARCHAR connection_id PK
    BIGINT id PK
    NUMERIC moment
  }
  connection_global {
    NUMERIC actuator_force
    VARCHAR connection_id PK
    BIGINT id PK
    NUMERIC story_drift_angle
  }
  connection_global_west {
    NUMERIC actuator_force
    VARCHAR connection_id PK
    BIGINT id PK
    NUMERIC story_drift_angle
  }
  connection_panel_zone {
    VARCHAR connection_id PK
    BIGINT id PK
    NUMERIC shear_distortion
    NUMERIC shear_force
  }
  database_readme {
    TEXT content
    VARCHAR database PK
  }
  dictionary_column {
    VARCHAR column_name PK
    VARCHAR database PK
    VARCHAR description
    VARCHAR example
    VARCHAR group
    BOOLEAN nullable
    SMALLINT position
    VARCHAR symbol
    VARCHAR type
    VARCHAR unit
  }
  ductile_fracture {
    FLOAT chemical_composition_Al
    FLOAT chemical_composition_C
    FLOAT chemical_composition_Cr
    FLOAT chemical_composition_Cu
    FLOAT chemical_composition_Mn
    FLOAT chemical_composition_Mo
    FLOAT chemical_composition_N
    FLOAT chemical_composition_Nb
    FLOAT chemical_composition_Ni
    FLOAT chemical_composition_P
    FLOAT chemical_composition_S
    FLOAT chemical_composition_Si
    FLOAT chemical_composition_Ti
    FLOAT chemical_composition_V
    VARCHAR coupon_direction
    VARCHAR crack_opening_direction
    FLOAT cvgm_etamono
    FLOAT cvgm_lambda
    SMALLINT date
    FLOAT disp_fract
    FLOAT elongation_fr
    SMALLINT epeq_simulation_count
    SMALLINT exc_at_fract
    VARCHAR experimental_program
    FLOAT f_un
    FLOAT f_yn
    SMALLINT force_elongation_count
    SMALLINT force_elongation_simulation_count
    SMALLINT force_radial_count
    SMALLINT force_radial_simulation_count
    VARCHAR fract_loc
    FLOAT fu_m
    FLOAT fy_m
    FLOAT gauge_length
    BOOLEAN has_sem
    VARCHAR id PK
    FLOAT kk_alpha_1
    FLOAT kk_alpha_2
    FLOAT kk_beta_1
    FLOAT kk_beta_2
    FLOAT kk_d_cr
    FLOAT l_star
    FLOAT latitude
    VARCHAR link
    VARCHAR loading
    VARCHAR loading_protocol
    VARCHAR location_coupon
    FLOAT lode_at_fr
    FLOAT lode_avg_till_fr
    SMALLINT lode_simulation_count
    FLOAT longitude
    VARCHAR meas_notch_diameter_cnt
    VARCHAR meas_notch_thickness_gp
    VARCHAR meas_notch_width
    VARCHAR meas_whole_diameter_cnt
    VARCHAR meas_whole_thickness_gp
    VARCHAR meas_width_gp
    FLOAT nom_notch_diameter_cnt
    FLOAT nom_notch_radius
    FLOAT nom_notch_thickness_gp
    FLOAT nom_notch_width
    FLOAT nom_whole_diameter_cnt
    FLOAT nom_whole_thickness_gp
    FLOAT nom_width_gp
    FLOAT nu
    FLOAT peeq_at_fr
    VARCHAR piece
    FLOAT plate_thickness
    VARCHAR reference
    VARCHAR section_profile
    VARCHAR section_type
    VARCHAR specimen_designation
    VARCHAR specimen_type
    VARCHAR steel_type
    INTEGER step_fract
    FLOAT swdfm_C
    FLOAT swdfm_alpha_neg
    FLOAT swdfm_alpha_pos
    FLOAT swdfm_beta
    FLOAT swdfm_kappa
    FLOAT temperature
    FLOAT triax_at_fr
    FLOAT triax_avg_till_fr
    SMALLINT triax_simulation_count
    FLOAT young_mod
  }
  ductile_fracture_epeq_simulation {
    VARCHAR ductile_fracture_id PK
    NUMERIC elongation
    BIGINT id PK
    NUMERIC peeq
  }
  ductile_fracture_force_elongation {
    VARCHAR ductile_fracture_id PK
    NUMERIC elongation
    BIGINT id PK
    NUMERIC load
  }
  ductile_fracture_force_elongation_simulation {
    VARCHAR ductile_fracture_id PK
    NUMERIC elongation
    BIGINT id PK
    NUMERIC load
  }
  ductile_fracture_force_radial {
    VARCHAR ductile_fracture_id PK
    NUMERIC elongation
    BIGINT id PK
    NUMERIC load
  }
  ductile_fracture_force_radial_simulation {
    VARCHAR ductile_fracture_id PK
    NUMERIC elongation
    BIGINT id PK
    NUMERIC load
  }
  ductile_fracture_lode_simulation {
    VARCHAR ductile_fracture_id PK
    NUMERIC elongation
    BIGINT id PK
    NUMERIC lode
  }
  ductile_fracture_triax_simulation {
    VARCHAR ductile_fracture_id PK
    NUMERIC elongation
    BIGINT id PK
    NUMERIC triaxiality
  }
  eccentric_braced_frame {
    FLOAT a_b_b
    FLOAT a_fil_n
    FLOAT a_m
    FLOAT a_n
    FLOAT af_m
    FLOAT af_n
    FLOAT aw_m
    FLOAT aw_n
    SMALLINT b_s_no
    FLOAT bf_m
    FLOAT bf_n
    VARCHAR class_aisc
    VARCHAR class_ec8
    FLOAT d_b_pnl_1
    FLOAT d_b_pnl_2
    FLOAT d_b_s
    SMALLINT e
    FLOAT e_m_flg
    FLOAT e_m_web
    INTEGER e_n_flg
    INTEGER e_n_web
    FLOAT f_u_exp_l_flg
    FLOAT f_u_exp_l_web
    FLOAT f_u_f_y_m_flg
    FLOAT f_u_f_y_m_web
    FLOAT f_u_f_y_n_flg
    FLOAT f_u_f_y_n_web
    FLOAT f_u_m_flg
    FLOAT f_u_m_web
    FLOAT f_u_n_flg
    FLOAT f_u_n_web
    FLOAT f_y_exp_l_flg
    FLOAT f_y_exp_l_web
    FLOAT f_y_m_flg
    FLOAT f_y_m_web
    FLOAT f_y_n_flg
    FLOAT f_y_n_web
    VARCHAR fail_mode
    FLOAT h_m
    FLOAT h_n
    FLOAT h_st
    FLOAT hw_m
    FLOAT hw_n
    VARCHAR id PK
    VARCHAR investigator
    VARCHAR l_bu_wld
    VARCHAR l_con_confi
    VARCHAR l_con_typ
    VARCHAR l_con_wld
    VARCHAR l_confi
    VARCHAR l_endp_wld
    VARCHAR l_p_typ
    FLOAT l_s_d_pnl_1_b
    FLOAT l_s_d_pnl_1_f
    FLOAT l_s_d_pnl_2_b
    FLOAT l_s_d_pnl_2_f
    INTEGER l_s_no_b
    INTEGER l_s_no_f
    VARCHAR l_s_reg
    VARCHAR l_s_side
    VARCHAR l_s_weld
    FLOAT l_st
    FLOAT latitude
    VARCHAR link_loc
    FLOAT longitude
    FLOAT n_d_n_pl_comp
    FLOAT n_d_n_pl_ten
    FLOAT ov_aisc
    FLOAT ov_ec8
    VARCHAR profile
    FLOAT r_n
    FLOAT r_t_flg
    FLOAT r_t_web
    FLOAT r_y_flg
    FLOAT r_y_web
    VARCHAR reference
    VARCHAR region
    VARCHAR sec_type
    VARCHAR sg_flg_link
    VARCHAR sg_web_link
    SMALLINT shear_link_angle_count
    VARCHAR spec_id
    FLOAT t_b_s
    FLOAT t_e_s
    FLOAT t_s
    FLOAT tf_add_m
    FLOAT tf_add_n
    FLOAT tf_m
    FLOAT tf_n
    FLOAT tw_m
    FLOAT tw_n
    VARCHAR url
    SMALLINT year
    FLOAT zp_fil_m
    FLOAT zp_fil_n
    FLOAT zp_m
    FLOAT zp_n
    FLOAT zp_no_fil_m
    FLOAT zp_no_fil_n
  }
  eccentric_braced_frame_shear_link_angle {
    VARCHAR eccentric_braced_frame_id PK
    NUMERIC gamma_t
    BIGINT id PK
    NUMERIC v
  }
  hss_column {
    FLOAT area__mm2
    FLOAT axial_load_ratio
    VARCHAR axial_load_sequence
    SMALLINT date
    FLOAT depth__mm
    FLOAT depth_over_t
    FLOAT f_ultimate__n_mm2
    FLOAT flange_thickness__mm
    VARCHAR flexural_buckling
    VARCHAR forming_process
    FLOAT fy_measured__n_mm2
    FLOAT fy_nominal__n_mm2
    VARCHAR id PK
    VARCHAR investigator
    FLOAT ke_measured__knmm_rad
    FLOAT lambda_c
    FLOAT lambda_s
    FLOAT latitude
    FLOAT length__mm
    SMALLINT loading_angle
    VARCHAR loading_protocol
    FLOAT longitude
    FLOAT mc_my_neg_100fit
    FLOAT mc_my_neg_80fit
    FLOAT mc_my_pos_100fit
    FLOAT mc_my_pos_80fit
    FLOAT moment_of_inertia__mm4
    SMALLINT moment_rotation_count
    FLOAT mp_measured__knmm
    FLOAT mu_mc_neg_100fit
    FLOAT mu_mc_neg_80fit
    FLOAT mu_mc_pos_100fit
    FLOAT mu_mc_pos_80fit
    FLOAT my_neg_100fit__knmm
    FLOAT my_neg_80fit__knmm
    FLOAT my_pos_100fit__knmm
    FLOAT my_pos_80fit__knmm
    FLOAT plastic_section_modulus__mm3
    FLOAT radius__mm
    VARCHAR reference
    VARCHAR seams
    VARCHAR steel_type
    SMALLINT stiffness_coefficient
    VARCHAR test_configuration
    VARCHAR test_type
    FLOAT theta_p_neg_100fit__rad
    FLOAT theta_p_neg_80fit__rad
    FLOAT theta_p_pos_100fit__rad
    FLOAT theta_p_pos_80fit__rad
    FLOAT theta_pc_neg_100fit__rad
    FLOAT theta_pc_neg_80fit__rad
    FLOAT theta_pc_pos_100fit__rad
    FLOAT theta_pc_pos_80fit__rad
    FLOAT theta_u_neg_100fit__rad
    FLOAT theta_u_neg_80fit__rad
    FLOAT theta_u_pos_100fit__rad
    FLOAT theta_u_pos_80fit__rad
    VARCHAR tube_section
    VARCHAR url
    FLOAT web_thickness__mm
    FLOAT width__mm
  }
  hss_column_moment_rotation {
    VARCHAR hss_column_id PK
    BIGINT id PK
    DOUBLE moment
    DOUBLE rotation
  }
  material {
    FLOAT al
    FLOAT avg_fractured_dia_bot__mm_
    FLOAT avg_fractured_dia_top__mm_
    FLOAT avg_reduced_dia__mm_
    FLOAT b
    FLOAT c
    FLOAT ca
    VARCHAR citekey
    FLOAT cr
    FLOAT cu
    DATE date
    FLOAT elastic_modulus__mpa_
    VARCHAR experimental_program
    FLOAT fe
    FLOAT fracture_strain
    FLOAT fu_n__mpa_
    FLOAT fy_n__mpa_
    FLOAT gage_length__mm_
    VARCHAR grade
    FLOAT h
    SMALLINT hidden_dataset_index
    SMALLINT hidden_index
    VARCHAR id PK
    VARCHAR investigator
    FLOAT latitude
    VARCHAR link
    VARCHAR location
    FLOAT longitude
    VARCHAR lp
    VARCHAR machine
    FLOAT mn
    FLOAT mo
    FLOAT n
    FLOAT nb
    FLOAT ni
    FLOAT p
    FLOAT pid_disp_k_p
    FLOAT pid_disp_t_d
    FLOAT pid_disp_t_i
    FLOAT pid_extenso_k_p
    FLOAT pid_extenso_t_d
    FLOAT pid_extenso_t_i
    FLOAT pid_force_k_p
    FLOAT pid_force_t_d
    FLOAT pid_force_t_i
    VARCHAR profile
    VARCHAR profile_type
    VARCHAR reference
    FLOAT s
    FLOAT si
    VARCHAR size
    FLOAT sn
    VARCHAR source
    VARCHAR spec
    SMALLINT stress_strain_count
    FLOAT t_a__deg_c_
    FLOAT thickness
    FLOAT ti
    FLOAT uvc_a
    FLOAT uvc_b
    FLOAT uvc_c1__mpa_
    FLOAT uvc_c2__mpa_
    FLOAT uvc_d__mpa_
    FLOAT uvc_e__gpa_
    FLOAT uvc_g1
    FLOAT uvc_g2
    FLOAT uvc_phi__prct_
    FLOAT uvc_q__mpa_
    FLOAT uvc_rho_d
    FLOAT uvc_rho_iso
    FLOAT uvc_rho_kin
    FLOAT uvc_rho_yield
    FLOAT uvc_sigma__mpa_
    FLOAT uvc_sigma_hard__mpa_
    FLOAT uvc_sigma_sat__mpa_
    FLOAT v
    FLOAT yield_stress__mpa_
    FLOAT zr
  }
  material_stress_strain {
    BIGINT id PK
    VARCHAR material_id PK
    NUMERIC strain
    NUMERIC stress
  }
  residual_stress {
    FLOAT A
    FLOAT b
    SMALLINT date
    SMALLINT distribution_F1_count
    SMALLINT distribution_F2_count
    SMALLINT distribution_W1_count
    VARCHAR experimental_program
    SMALLINT flange_nr_data
    FLOAT fy_e
    FLOAT fy_mf
    FLOAT fy_mw
    FLOAT fy_n
    FLOAT h
    VARCHAR id PK
    NUMERIC latitude
    VARCHAR link
    NUMERIC longitude
    NUMERIC plot_sf
    VARCHAR profile
    VARCHAR profile_type
    SMALLINT qp_coefficient_count
    FLOAT r
    VARCHAR reference
    NUMERIC sigma_0_f
    NUMERIC sigma_0_w
    VARCHAR spec_var
    VARCHAR steel
    FLOAT tf
    FLOAT tw
  }
  residual_stress_distribution_f1 {
    NUMERIC coordinate
    BIGINT id PK
    NUMERIC residual_stress
    VARCHAR residual_stress_id PK
  }
  residual_stress_distribution_f2 {
    NUMERIC coordinate
    BIGINT id PK
    NUMERIC residual_stress
    VARCHAR residual_stress_id PK
  }
  residual_stress_distribution_w1 {
    NUMERIC coordinate
    BIGINT id PK
    NUMERIC residual_stress
    VARCHAR residual_stress_id PK
  }
  residual_stress_qp_coefficient {
    BIGINT id PK
    NUMERIC qp_coefficient
    VARCHAR residual_stress_id PK
  }
  tensile_coupon {
    FLOAT al
    FLOAT avg_fractured_marked_gauge_length__mm_
    FLOAT avg_init_marked_gauge_length__mm_
    FLOAT avg_init_reduced_thickness__mm_
    FLOAT avg_init_reduced_width__mm_
    FLOAT b
    BOOLEAN bin_discont_yield
    FLOAT c
    FLOAT ca
    FLOAT cr
    FLOAT cu
    SMALLINT datacol_version
    VARCHAR date
    FLOAT eff_fractured_thickness__mm_
    FLOAT eff_fractured_width__mm_
    FLOAT elastic_modulus__mpa_
    FLOAT elongation_after_fracture
    FLOAT elongation_at_fracture
    VARCHAR experimental_program
    FLOAT fe
    VARCHAR file_path
    FLOAT fu_n__mpa_
    FLOAT fy_n__mpa_
    FLOAT h
    VARCHAR id PK
    VARCHAR investigator
    FLOAT latitude
    VARCHAR link
    VARCHAR location
    FLOAT longitude
    VARCHAR machine
    FLOAT mn
    FLOAT mo
    FLOAT n
    FLOAT nb
    FLOAT ni
    FLOAT p
    FLOAT pid_disp_d
    FLOAT pid_disp_i
    FLOAT pid_disp_p
    FLOAT pid_ext_d
    FLOAT pid_ext_i
    FLOAT pid_ext_p
    FLOAT pid_force_d
    FLOAT pid_force_i
    FLOAT pid_force_p
    VARCHAR profile
    VARCHAR profile_type
    VARCHAR publication_key
    FLOAT reduction_of_area
    VARCHAR reference
    FLOAT s
    FLOAT si
    FLOAT sn
    VARCHAR specimen_source
    VARCHAR specimen_type
    VARCHAR standard
    VARCHAR steel_grade
    SMALLINT stress_strain_count
    FLOAT t_a__deg_c_
    FLOAT tensile_strength__mpa_
    FLOAT ti
    FLOAT uniform_elongation
    FLOAT v
    SMALLINT year
    FLOAT yield_point_elongation
    FLOAT yield_strain_02
    FLOAT yield_stress_02__mpa_
    FLOAT yield_stress_lyp__mpa_
    FLOAT yield_stress_uyp__mpa_
    FLOAT zr
  }
  tensile_coupon_stress_strain {
    BIGINT id PK
    NUMERIC strain
    NUMERIC stress
    VARCHAR tensile_coupon_id PK
  }
  auth_user ||--o{ auth_identity : "user_id"
  auth_user ||--o{ auth_login_challenge : "link_user_id"
  auth_user ||--o{ auth_session : "user_id"
  brace ||--o{ brace_displacement : "brace_id"
  column ||--o{ column_axial_shortening : "column_id"
  column ||--o{ column_moment_strong : "column_id"
  column ||--o{ column_moment_weak : "column_id"
  connection ||--o{ connection_beam : "connection_id"
  connection ||--o{ connection_beam_west : "connection_id"
  connection ||--o{ connection_global : "connection_id"
  connection ||--o{ connection_global_west : "connection_id"
  connection ||--o{ connection_panel_zone : "connection_id"
  ductile_fracture ||--o{ ductile_fracture_epeq_simulation : "ductile_fracture_id"
  ductile_fracture ||--o{ ductile_fracture_force_elongation : "ductile_fracture_id"
  ductile_fracture ||--o{ ductile_fracture_force_elongation_simulation : "ductile_fracture_id"
  ductile_fracture ||--o{ ductile_fracture_force_radial : "ductile_fracture_id"
  ductile_fracture ||--o{ ductile_fracture_force_radial_simulation : "ductile_fracture_id"
  ductile_fracture ||--o{ ductile_fracture_lode_simulation : "ductile_fracture_id"
  ductile_fracture ||--o{ ductile_fracture_triax_simulation : "ductile_fracture_id"
  eccentric_braced_frame ||--o{ eccentric_braced_frame_shear_link_angle : "eccentric_braced_frame_id"
  hss_column ||--o{ hss_column_moment_rotation : "hss_column_id"
  material ||--o{ material_stress_strain : "material_id"
  residual_stress ||--o{ residual_stress_distribution_f1 : "residual_stress_id"
  residual_stress ||--o{ residual_stress_distribution_f2 : "residual_stress_id"
  residual_stress ||--o{ residual_stress_distribution_w1 : "residual_stress_id"
  residual_stress ||--o{ residual_stress_qp_coefficient : "residual_stress_id"
  tensile_coupon ||--o{ tensile_coupon_stress_strain : "tensile_coupon_id"
```
