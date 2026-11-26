import type { DictColumn } from '@/stores/dictionary'
import { FIELD_GROUPS, groupBy, groupFor, groupOrder, type FieldGroupId } from '@/utils/fieldGroups'
import type { DatabaseId } from '@/utils/navigation'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

/**
 * `database-columns.json` (repo root, committed) is the column list of every
 * database, in dictionary order. The backend writes it from the ORM models
 * (`make api`, also run by `make generate-model`), and the backend test
 * `test_database_columns.py` fails when it is stale. So the taxonomy is checked
 * against the real schema, with nothing to generate before the test runs.
 */
// Resolved in two steps on purpose: Vite rewrites `new URL('literal',
// import.meta.url)` into an asset import, which would try to bundle the file
// instead of reading it.
const COLUMNS_FILE = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '../../../../database-columns.json'
)

const COLUMNS = JSON.parse(readFileSync(COLUMNS_FILE, 'utf-8')) as Record<DatabaseId, string[]>

const DATABASES = Object.keys(COLUMNS) as DatabaseId[]

function columnNames(database: DatabaseId): string[] {
  return COLUMNS[database]
}

function column(name: string, group?: string): DictColumn {
  return {
    name,
    description: name,
    symbol: '-',
    unit: '-',
    type: 'String',
    example: '',
    nullable: true,
    group
  }
}

function tally(database: DatabaseId): Record<string, number> {
  const counts: Record<string, number> = {}
  columnNames(database).forEach((name) => {
    const id = groupFor(database, column(name))
    counts[id] = (counts[id] ?? 0) + 1
  })
  return counts
}

describe('fieldGroups: coverage of the real schema', () => {
  it.each(DATABASES)('classifies every column of %s', (database) => {
    const orphans = columnNames(database).filter(
      (name) => groupFor(database, column(name)) === 'other'
    )
    expect(orphans).toEqual([])
  })

  it.each(DATABASES)('puts the review status with the program details in %s', (database) => {
    // Set by the Hub (#253), so the column list above never carries it.
    expect(groupFor(database, column('data_curation_status'))).toBe('experimental_program_details')
  })

  it.each(DATABASES)('declares no group that never matches in %s', (database) => {
    // A rule that claims nothing is a typo: groupBy silently drops empty groups,
    // so without this the mistake would only show up as a missing group in the UI.
    const filled = new Set(Object.keys(tally(database)))
    const declared = FIELD_GROUPS[database].map((rule) => rule.id)
    expect(declared.filter((id) => !filled.has(id))).toEqual([])
  })
})

describe('fieldGroups: group sizes', () => {
  // The counts the researchers agreed on in resslab-hub-data#46. They are the
  // contract between this module and the `group` column of the dictionaries.
  it('splits the 153 columns of connections into fourteen groups', () => {
    expect(tally('connections')).toEqual({
      experimental_program_details: 10,
      connection_detailing: 7,
      beam_section_properties: 24,
      beam_material_properties: 6,
      specimen_dimensions: 5,
      column_section_properties: 14,
      column_material_properties: 7,
      weld_details: 7,
      concrete_slab_properties: 22,
      panel_zone_geometric_properties: 19,
      panel_zone_resistance: 14,
      panel_zone_demand: 7,
      panel_zone_demand_to_resistance_ratio: 8,
      panel_zone_shear_distortion: 3
    })
  })

  it('splits the 48 columns of residual stresses into seven groups', () => {
    expect(tally('residuals')).toEqual({
      experimental_program_details: 9,
      steel_profile: 2,
      material_properties: 8,
      section_properties: 9,
      fabrication_details: 13,
      measured_residual_stresses: 6,
      plot_properties: 1
    })
  })

  it('splits the 71 columns of braces into ten groups', () => {
    expect(tally('braces')).toEqual({
      experimental_program_details: 8,
      section_properties: 14,
      specimen_details: 5,
      material_properties: 5,
      brace_member_geometric_properties: 5,
      gusset_plate_dimensions: 18,
      gusset_plate_material_properties: 4,
      connection_detailing: 8,
      loading_details: 1,
      measured_and_theoretical_resistance: 3
    })
  })

  it('splits the 70 columns of tensile coupons into seven groups', () => {
    expect(tally('tensile')).toEqual({
      experimental_program_details: 13,
      specimen_details: 5,
      material_properties: 12,
      geometric_properties: 6,
      test_equipment_details: 10,
      elongation_and_reduction_of_area: 4,
      chemical_composition: 20
    })
  })

  it('keeps every database under a scannable number of groups', () => {
    DATABASES.forEach((database) => {
      expect(FIELD_GROUPS[database].length).toBeLessThanOrEqual(14)
    })
  })
})

describe('fieldGroups: element symbols never leak across databases', () => {
  // The chemistry rule is only reachable from the material databases. Applied
  // globally it would swallow real structural variables that happen to be spelled
  // like an element.
  it('reads b as boron in a coupon and as the section width elsewhere', () => {
    expect(groupFor('tensile', column('b'))).toBe('chemical_composition')
    expect(groupFor('cyclic', column('b'))).toBe('chemical_composition')
    expect(groupFor('residuals', column('b'))).toBe('section_properties')
  })

  it('reads h as hydrogen in a coupon and as the section height elsewhere', () => {
    expect(groupFor('cyclic', column('h'))).toBe('chemical_composition')
    expect(groupFor('residuals', column('h'))).toBe('section_properties')
  })

  it('reads p as phosphorus in a coupon and as the axial load in columns', () => {
    expect(groupFor('tensile', column('p'))).toBe('chemical_composition')
    expect(groupFor('columns', column('p'))).toBe('loading_details')
  })
})

describe('fieldGroups: name-driven rules', () => {
  it('groups the two HSS backbone calibrations separately', () => {
    expect(groupFor('hss', column('theta_p_pos_100fit__rad'))).toBe(
      'backbone_parameters_100_percent_fit'
    )
    expect(groupFor('hss', column('mc_my_neg_80fit'))).toBe('backbone_parameters_80_percent_fit')
  })

  it('picks up a new prefixed column with no rule change', () => {
    expect(groupFor('cyclic', column('uvc_rho_new'))).toBe('cyclic_material_model_parameters')
    expect(groupFor('ductile-fracture', column('swdfm_gamma'))).toBe('fracture_model_parameters')
    expect(groupFor('tensile', column('pid_torque_p'))).toBe('test_equipment_details')
  })

  it('matches regardless of the casing the dictionary uses', () => {
    expect(groupFor('braces', column('specimen_ID'))).toBe('experimental_program_details')
    expect(groupFor('ductile-fracture', column('chemical_composition_Mn'))).toBe(
      'chemical_composition'
    )
    expect(groupFor('residuals', column('A'))).toBe('section_properties')
  })
})

describe('fieldGroups: dictionary override', () => {
  // The dictionary spells groups the way a reader reads them; the id is derived.
  it('prefers the group carried by the data dictionary', () => {
    expect(groupFor('residuals', column('b', 'Material properties'))).toBe('material_properties')
    expect(groupFor('hss', column('anything', 'Backbone parameters (100% fit)'))).toBe(
      'backbone_parameters_100_percent_fit'
    )
  })

  it('knows the two groups the #245 review added', () => {
    // Both are new labels, so a typo here would send the column through the regex
    // fallback instead and the dictionary would silently lose the group.
    expect(groupFor('braces', column('kl_r', 'Brace member geometric properties'))).toBe(
      'brace_member_geometric_properties'
    )
    expect(
      groupFor('tensile', column('reduction_of_area', 'Elongation and reduction of area'))
    ).toBe('elongation_and_reduction_of_area')
  })

  it('falls back to the rules for a group it does not know', () => {
    expect(groupFor('residuals', column('b', 'Not a group'))).toBe('section_properties')
  })
})

describe('fieldGroups: groupBy', () => {
  const items = ['sigma_0_f', 'id', 'steel', 'date'].map((name) => column(name))

  it('returns groups in rule order, not in input order', () => {
    expect(groupBy('residuals', items, (item) => item).map((group) => group.id)).toEqual([
      'experimental_program_details',
      'material_properties',
      'measured_residual_stresses'
    ])
  })

  it('keeps the members of a group in input order', () => {
    const first = groupBy('residuals', items, (item) => item)[0]
    expect(first.items.map((item) => item.name)).toEqual(['id', 'date'])
  })

  it('drops groups nothing landed in', () => {
    const ids = groupBy('residuals', items, (item) => item).map((group) => group.id)
    expect(ids).not.toContain('section_properties')
  })

  it('sends an unclaimed column to the catch-all, last', () => {
    const groups = groupBy('residuals', [column('brand_new_column')], (item) => item)
    expect(groups).toEqual([{ id: 'other', items: [column('brand_new_column')] }])
  })
})

describe('fieldGroups: groupOrder', () => {
  it('ends with the catch-all so an unclaimed column never jumps the list', () => {
    const order: FieldGroupId[] = groupOrder('braces')
    expect(order[0]).toBe('experimental_program_details')
    expect(order[order.length - 1]).toBe('other')
  })
})

describe('fieldGroups: ratios land where a reader looks for them', () => {
  // `_over_` alone is not enough of a signal: a columns test reports both
  // geometric slenderness ratios and axial load ratios in the same notation.
  it('separates slenderness ratios from load ratios', () => {
    expect(groupFor('columns', column('h_over_t_cw'))).toBe(
      'slenderness_and_section_classification'
    )
    expect(groupFor('columns', column('p_g_over_p_ym'))).toBe('loading_details')
    // Dimitrios read every `p_*_over_*` as a load ratio in the #245 review, so the
    // axial resistance group keeps the resistances themselves and nothing else.
    expect(groupFor('columns', column('p_c_over_p_yn'))).toBe('loading_details')
    expect(groupFor('columns', column('p_c'))).toBe('axial_resistance')
  })
})
