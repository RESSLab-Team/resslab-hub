/**
 * Scientific categories for a database's variables.
 *
 * A database carries between 25 and 153 columns, and every surface that renders
 * them (the filter rail, the contribution editor, the curation review panel, the
 * specimen drawer) used to render one flat list. This module gives every column a
 * category so those surfaces can collapse them into groups a structural engineer
 * recognises: the beam, the panel zone, the chemistry, the calibrated model
 * parameters.
 *
 * Rules are ordered per database and the first match wins, so the rule order is
 * also the group order in the UI. Prefer a regex whenever the schema already
 * encodes the group in the name (`uvc_`, `pid_`, `chemical_composition_`,
 * `_100fit`): a column added to the data dictionary then lands in the right group
 * with no edit here. Explicit names are for the splits the naming does not carry,
 * such as which of a connection's dimensions belong to the beam and which to the
 * column.
 *
 * The eventual home for this is a `category` column in the data dictionary itself,
 * owned by the researchers rather than by the frontend. {@link groupFor} already
 * prefers `DictColumn.category` when it is present, so that migration needs no
 * change on this side.
 */
import type { DictColumn } from '@/stores/dictionary'
import type { DatabaseId } from '@/utils/navigation'

export type FieldGroupId =
  | 'identification'
  | 'test_setup'
  | 'section'
  | 'geometry'
  | 'geometry_measured'
  | 'slenderness'
  | 'material'
  | 'chemistry'
  | 'detailing'
  | 'welds'
  | 'gusset_plate'
  | 'stiffeners'
  | 'composite_slab'
  | 'beam'
  | 'column_member'
  | 'panel_zone'
  | 'panel_zone_strength'
  | 'loading'
  | 'capacity'
  | 'demand'
  | 'response'
  | 'residual_stress'
  | 'backbone_100fit'
  | 'backbone_80fit'
  | 'model_parameters'
  | 'instrumentation'
  | 'imaging'
  | 'provenance'
  | 'internal'
  | 'other'

/** First match wins, so the order of the rules is the order of the groups. */
export interface FieldGroupRule {
  id: FieldGroupId
  /** Column names (lower case) or patterns tested against the lower-cased name. */
  match: (string | RegExp)[]
}

/** Where a column ends up when no rule claims it. Audited in dev, never expected. */
export const FALLBACK_GROUP: FieldGroupId = 'other'

/**
 * Bare element symbols, only reachable from the material databases that report a
 * chemical composition.
 *
 * This regex must never be applied globally: `b` is boron here but the section
 * width in residual stresses, `h` is hydrogen here but the section height there,
 * and `p` is phosphorus here but the applied axial load in the columns database.
 */
const ELEMENT_SYMBOL = /^(c|si|mn|p|s|n|cu|mo|ni|cr|v|nb|ti|al|b|zr|sn|ca|h|fe)$/

/** PID gains of the test frame, the same nine columns in cyclic and tensile. */
const PID_GAIN = /^pid_/

const PROVENANCE = ['reference', 'link', 'url', 'latitude', 'longitude']

export const FIELD_GROUPS: Record<DatabaseId, FieldGroupRule[]> = {
  connections: [
    {
      id: 'identification',
      match: ['id', 'experimental_program', 'date', 'specimen_designation', 'comments']
    },
    {
      id: 'test_setup',
      match: ['northridge', 'specimen_type', 'loading_protocol', 'slab', 'connection_type']
    },
    // Reduced beam section cut and continuity plates: what makes the connection
    // this connection, as opposed to the members it joins.
    { id: 'detailing', match: ['t_pl', 'rbs_cut', 's_h', 'd_h'] },
    {
      id: 'beam',
      match: [
        'section_b',
        'd_b',
        'd_bg',
        't_bw',
        'b_bf',
        't_bf',
        'r_b',
        'a_b',
        'i_xb',
        'z_xb',
        'z_xb_bfp',
        'r_yb',
        'b_bf_rbs',
        'd_gb_rbs',
        'a_b_rbs',
        'i_xb_rbs',
        'z_xb_rbs',
        'd_bm',
        'd_bgm',
        't_bwm',
        'b_bfm',
        't_bfm',
        'z_xbm',
        'steel_b',
        'f_yb',
        'f_ybw',
        'f_ybf',
        'f_yb_mill',
        'f_yb_avg',
        'l_b',
        'l_fc',
        'l_o',
        'lo_db'
      ]
    },
    {
      id: 'column_member',
      match: [
        'section_c',
        'section_shape_c',
        'd_c',
        't_cw',
        'b_cf',
        'c_c',
        't_cf',
        'r_c',
        'a_c',
        'i_xc',
        'd_cm',
        't_wcm',
        'c_cm',
        'b_fcm',
        't_fcm',
        'steel_c',
        'f_yc',
        'f_ydp',
        'f_ycw',
        'f_ycf',
        'f_yc_mill',
        'f_yc_avg',
        'h_c'
      ]
    },
    // Weld metal toughness and the weld access hole that fractures start from.
    {
      id: 'welds',
      match: [
        'backing_bar',
        'electrode',
        'd_electrode',
        /^cvn_/,
        'access_hole_geometry',
        'w',
        'w_l',
        'w_r',
        'h_t'
      ]
    },
    {
      id: 'composite_slab',
      match: [
        'a_s',
        'f_sk',
        'f_sm',
        'h_co',
        'slab_con_type',
        'f_ck',
        'f_cm',
        'cur_days',
        'f_c_compr_calc',
        'd',
        'h_sc',
        'n_studs',
        'n_diss',
        'n_r',
        'f_u_sc',
        'h_p',
        'b_o',
        'deck_ribs_orientation'
      ]
    },
    {
      id: 'panel_zone',
      match: [
        /_pz$/,
        'dz',
        'zw',
        'dz_plug',
        'wz_plug',
        'wd',
        'n_dp',
        't_dp',
        't_dp_tot',
        't_p',
        't_cp',
        'd_cp',
        'db_plus',
        'db_minus',
        'a_vc'
      ]
    },
    // Panel-zone strength predicted by each code (Eurocode, AISC, AIJ).
    {
      id: 'panel_zone_strength',
      match: [/^fy_pz_/, /^p_c[mn]$/, /^n_p[mn]$/, /_europe$/, /_aisc$/, /_aij$/]
    },
    // What the test actually demanded of the panel zone, and the resulting ratios.
    {
      id: 'demand',
      match: [/^m_cf_/, /^v_bf_/, 'v_col_n', /^r_u_/, /^ru_rn_/, /^aisc_pz_violation_/]
    },
    { id: 'response', match: ['g_max', 'g_y', 'g_max_g_y'] },
    { id: 'provenance', match: PROVENANCE }
  ],

  columns: [
    {
      id: 'identification',
      match: ['id', 'experimental_program', 'date', 'specimen_designation', 'comments']
    },
    {
      id: 'geometry',
      match: [
        'section_c',
        'd_c',
        'k_c',
        'k1_c',
        'h_c',
        't_cw',
        'b_cf',
        't_cf',
        'a_cm',
        'a_cn',
        'i_xb',
        'i_xc',
        's_xc',
        's_yc',
        'z_xc',
        'z_yc',
        'j_c',
        'c_wc',
        'r_yc',
        'r_xc',
        'l_c',
        'l_sc',
        'l_bc',
        't_top_plate',
        't_bottom_plate'
      ]
    },
    // Width-to-thickness and slenderness ratios plus the section class they drive,
    // under both the US and the European classification. Anchored on the numerator
    // so it cannot swallow the `p_*_over_p_*` axial load ratios below.
    {
      id: 'slenderness',
      match: [/^(h|b_f|l_b)_over_/, /^k_[xy]c$/, /^lambda_/, /_class_(us|eu)$/]
    },
    {
      id: 'material',
      match: [
        'steel_c',
        'r_y',
        'r_t',
        'f_ymf',
        'f_ymw',
        'f_umf',
        'f_umw',
        'f_yn',
        'f_un',
        'e_nc',
        'e_mc',
        'g_nc',
        'g_mc'
      ]
    },
    // The applied loads live here rather than under capacity: the axial load ratio
    // is what a reader is looking for when they think about how a column was tested.
    {
      id: 'loading',
      match: [
        'boundary_condition',
        'lateral_lp',
        'direction_lp',
        'axis_of_bending',
        'axial_lp',
        'test_procedure',
        'cfe',
        'p_g',
        'p',
        /^p_g_over_/
      ]
    },
    // Yield and buckling capacities, and the demands normalised by them.
    { id: 'capacity', match: [/^p_y[mne]$/, 'p_t', 'p_c', /^p_[tc]_over_/] },
    // Measured stiffness and the chord rotations at each strength-loss threshold.
    { id: 'response', match: [/^k_/, /^th_/, /^d_(80|50|20)$/] },
    { id: 'provenance', match: PROVENANCE }
  ],

  braces: [
    { id: 'identification', match: ['id', 'investigator', 'specimen_id', 'date'] },
    {
      id: 'geometry',
      match: [
        'cross_section_shape',
        'cross_section_size',
        'area',
        'd_br',
        'b_br',
        't_br',
        'w_br',
        'i_x',
        'i_y',
        'r_x',
        'r_y',
        'z_x',
        'z_y',
        'j'
      ]
    },
    {
      id: 'test_setup',
      match: ['configuration', 'brace_angle', 'l_b', 'l_b_clear', 'boundary_condition']
    },
    { id: 'material', match: ['steel', 'e', 'f_yn', 'fy_m', 'f_um'] },
    // Both gusset plates (top and bottom) and everything that attaches the brace to
    // them. `_8t` really is spelled with a leading underscore in the dictionary.
    {
      id: 'gusset_plate',
      match: [
        /^l_[1-8][tb]$/,
        '_8t',
        't_t',
        't_b',
        /_gp$/,
        'weld_type',
        'l_weld',
        't_weld',
        'stick_space',
        'nub_bolts',
        'bolt_size',
        'bolt_mat',
        'reinforcement_pl'
      ]
    },
    { id: 'loading', match: ['loading_protocol'] },
    // Measured and theoretical buckling capacity, with the slenderness behind it.
    { id: 'capacity', match: ['p_t', 'p_t_theory', 'p_c', /^kl_r/, /^l_c/, 'k_assumed'] },
    { id: 'provenance', match: PROVENANCE }
  ],

  hss: [
    { id: 'identification', match: ['id', 'date', 'investigator'] },
    {
      id: 'test_setup',
      match: ['test_configuration', 'stiffness_coefficient', 'test_type', 'flexural_buckling']
    },
    {
      id: 'loading',
      match: ['loading_protocol', 'axial_load_ratio', 'axial_load_sequence', 'loading_angle']
    },
    { id: 'section', match: ['forming_process', 'seams', 'tube_section'] },
    {
      id: 'geometry',
      match: [
        'width__mm',
        'depth__mm',
        'flange_thickness__mm',
        'web_thickness__mm',
        'area__mm2',
        'moment_of_inertia__mm4',
        'radius__mm',
        'plastic_section_modulus__mm3',
        'length__mm'
      ]
    },
    { id: 'slenderness', match: ['depth_over_t', 'lambda_s', 'lambda_c'] },
    { id: 'material', match: [/^fy_/, 'f_ultimate__n_mm2', 'steel_type'] },
    { id: 'capacity', match: ['mp_measured__knmm', 'ke_measured__knmm_rad'] },
    // Modified Ibarra-Medina-Krawinkler backbone, calibrated twice: once on the
    // full response and once on the response truncated at 80 percent of capacity.
    { id: 'backbone_100fit', match: [/_100fit(__.+)?$/] },
    { id: 'backbone_80fit', match: [/_80fit(__.+)?$/] },
    { id: 'provenance', match: PROVENANCE }
  ],

  ebf: [
    { id: 'identification', match: ['id', 'investigator', 'year', 'spec_id', 'region'] },
    // The link itself: what it is made of and how it classifies under each code.
    {
      id: 'section',
      match: [
        'profile',
        'sec_type',
        'e',
        'link_loc',
        'l_confi',
        'class_aisc',
        'class_ec8',
        'ov_aisc',
        'ov_ec8'
      ]
    },
    // Flange and web are reported separately for every material property.
    { id: 'material', match: [/_(flg|web)$/, 'sg_flg_link', 'sg_web_link'] },
    { id: 'geometry', match: [/_n$/] },
    { id: 'geometry_measured', match: [/_m$/] },
    { id: 'stiffeners', match: [/^l_s_/, 't_s'] },
    {
      id: 'welds',
      match: [
        /^l_con_/,
        /_wld$/,
        'l_st',
        'h_st',
        'a_b_b',
        't_e_s',
        't_b_s',
        'd_b_s',
        /^d_b_pnl_/,
        'b_s_no'
      ]
    },
    { id: 'loading', match: ['l_p_typ', /^n_d_n_pl_/] },
    { id: 'response', match: ['fail_mode'] },
    { id: 'provenance', match: PROVENANCE }
  ],

  cyclic: [
    {
      id: 'identification',
      match: ['id', 'experimental_program', 'investigator', 'date', 'location']
    },
    // Which piece of which profile the coupon was cut from.
    {
      id: 'section',
      match: ['profile_type', 'profile', 'source', 'thickness', 'grade', 'spec', 'lp', 'size']
    },
    { id: 'geometry', match: ['gage_length__mm_', /^avg_.*_dia_/] },
    {
      id: 'material',
      match: [
        'fy_n__mpa_',
        'fu_n__mpa_',
        't_a__deg_c_',
        'yield_stress__mpa_',
        'elastic_modulus__mpa_',
        'fracture_strain'
      ]
    },
    { id: 'chemistry', match: [ELEMENT_SYMBOL] },
    { id: 'instrumentation', match: ['machine', PID_GAIN] },
    // Updated Voce-Chaboche parameters calibrated on the cyclic response.
    { id: 'model_parameters', match: [/^uvc_/] },
    { id: 'provenance', match: [...PROVENANCE, 'file', 'citekey'] },
    { id: 'internal', match: [/^hidden_/] }
  ],

  tensile: [
    {
      id: 'identification',
      match: ['id', 'experimental_program', 'investigator', 'date', 'year', 'location']
    },
    {
      id: 'section',
      match: ['standard', 'specimen_type', 'profile_type', 'profile', 'specimen_source']
    },
    { id: 'geometry', match: [/^avg_init_/, /^eff_fractured_/, /^avg_fractured_/] },
    { id: 'material', match: ['steel_grade', 'fy_n__mpa_', 'fu_n__mpa_', 't_a__deg_c_'] },
    // Everything read off the measured stress-strain curve.
    {
      id: 'response',
      match: [
        /^yield_/,
        'bin_discont_yield',
        'tensile_strength__mpa_',
        /elongation/,
        'reduction_of_area',
        'elastic_modulus__mpa_'
      ]
    },
    { id: 'chemistry', match: [ELEMENT_SYMBOL] },
    { id: 'instrumentation', match: ['machine', PID_GAIN] },
    { id: 'provenance', match: [...PROVENANCE, 'file_path', 'publication_key'] },
    { id: 'internal', match: ['datacol_version'] }
  ],

  'ductile-fracture': [
    { id: 'identification', match: ['id', 'specimen_designation', 'experimental_program', 'date'] },
    {
      id: 'section',
      match: [
        'specimen_type',
        'piece',
        'location_coupon',
        'section_type',
        'section_profile',
        'coupon_direction',
        'crack_opening_direction',
        'plate_thickness'
      ]
    },
    { id: 'loading', match: ['loading', 'loading_protocol', 'temperature'] },
    {
      id: 'material',
      match: ['steel_type', 'f_yn', 'f_un', 'fy_m', 'fu_m', 'elongation_fr', 'young_mod', 'nu']
    },
    { id: 'chemistry', match: [/^chemical_composition_/] },
    { id: 'geometry', match: ['gauge_length', /^nom_/] },
    { id: 'geometry_measured', match: [/^meas_/] },
    // Stress state and equivalent plastic strain at the instant of fracture.
    {
      id: 'response',
      match: [
        'disp_fract',
        'exc_at_fract',
        'step_fract',
        'fract_loc',
        /^triax_/,
        /^lode_/,
        'peeq_at_fr',
        'l_star'
      ]
    },
    // Cyclic void growth, stress-weighted damage and Kanvinde-Kiran parameters.
    { id: 'model_parameters', match: [/^(cvgm|swdfm|kk)_/] },
    { id: 'imaging', match: ['has_sem'] },
    { id: 'provenance', match: PROVENANCE }
  ],

  residuals: [
    { id: 'identification', match: ['id', 'experimental_program', 'date'] },
    {
      id: 'geometry',
      match: ['profile_type', 'profile', 'spec_var', 'h', 'b', 'tw', 'tf', 'r', 'a']
    },
    { id: 'material', match: ['steel', /^fy_/] },
    // The measured self-equilibrating stresses in the flanges and the web.
    { id: 'residual_stress', match: [/^sigma_0_/] },
    { id: 'provenance', match: PROVENANCE },
    { id: 'internal', match: ['flange_nr_data', 'plot_sf'] }
  ]
}

const KNOWN_GROUPS = new Set<string>(
  Object.values(FIELD_GROUPS).flatMap((rules) => rules.map((rule) => rule.id))
)

// One name -> group lookup per database, built on first use. The resolver runs once
// per column per render across four surfaces, so the regex sweep is worth caching.
const resolved = new Map<DatabaseId, Map<string, FieldGroupId>>()

function matches(name: string, pattern: string | RegExp): boolean {
  return typeof pattern === 'string' ? pattern === name : pattern.test(name)
}

function resolve(database: DatabaseId, name: string): FieldGroupId {
  let cache = resolved.get(database)
  if (!cache) {
    cache = new Map()
    resolved.set(database, cache)
  }
  const cached = cache.get(name)
  if (cached) return cached
  const rule = FIELD_GROUPS[database]?.find((entry) =>
    entry.match.some((pattern) => matches(name, pattern))
  )
  const id = rule?.id ?? FALLBACK_GROUP
  cache.set(name, id)
  return id
}

/**
 * The category of one column.
 *
 * A `category` carried by the data dictionary wins, which is how this module stops
 * being the source of truth once the data repo owns the taxonomy. An unrecognised
 * category falls through to the rules rather than producing an unlabelled group.
 */
export function groupFor(database: DatabaseId, column: DictColumn): FieldGroupId {
  const declared = column.category?.trim().toLowerCase()
  if (declared && KNOWN_GROUPS.has(declared)) return declared as FieldGroupId
  return resolve(database, column.name.trim().toLowerCase())
}

/** The groups of a database, in rule order, with the catch-all last. */
export function groupOrder(database: DatabaseId): FieldGroupId[] {
  return [...(FIELD_GROUPS[database]?.map((rule) => rule.id) ?? []), FALLBACK_GROUP]
}

/**
 * Split any dictionary-backed list into ordered groups. Empty groups are dropped,
 * so a database whose rows never fill a group simply does not show it.
 */
export function groupBy<T>(
  database: DatabaseId,
  items: T[],
  columnOf: (item: T) => DictColumn
): { id: FieldGroupId; items: T[] }[] {
  const buckets = new Map<FieldGroupId, T[]>()
  items.forEach((item) => {
    const id = groupFor(database, columnOf(item))
    const bucket = buckets.get(id)
    if (bucket) bucket.push(item)
    else buckets.set(id, [item])
  })
  return groupOrder(database)
    .filter((id) => buckets.has(id))
    .map((id) => ({ id, items: buckets.get(id)! }))
}
