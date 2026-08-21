import type { DictColumn } from '@/stores/dictionary'
import { FIELD_GROUPS, groupBy, groupFor, groupOrder, type FieldGroupId } from '@/utils/fieldGroups'
import type { DatabaseId } from '@/utils/navigation'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

/**
 * The checked-in sample CSVs carry the exact column list of every database, in
 * dictionary order, and they are regenerated from the data repo whenever the
 * schema moves. Reading their headers here means the taxonomy is checked against
 * the real schema rather than against a fixture someone has to remember to update.
 */
const SAMPLE_CSV: Record<DatabaseId, string> = {
  connections: 'connections/connections.csv',
  columns: 'columns/steel_columns.csv',
  braces: 'braces/steel_braces.csv',
  hss: 'hss_columns/hss_columns.csv',
  ebf: 'eccentric_braced_frames/eccentric_braced_frames.csv',
  cyclic: 'material/cyclic_coupons/steel_material.csv',
  tensile: 'material/tensile_coupons/tensile_coupons.csv',
  'ductile-fracture': 'material/ductile_fracture/ductile_fracture.csv',
  residuals: 'residual_stresses/residual_stresses.csv'
}

const DATABASES = Object.keys(SAMPLE_CSV) as DatabaseId[]

// Resolved in two steps on purpose: Vite rewrites `new URL('literal',
// import.meta.url)` into an asset import, which would try to bundle the sample
// data instead of reading it.
const SAMPLE_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../../../../sample-data')

function columnNames(database: DatabaseId): string[] {
  const header = readFileSync(resolve(SAMPLE_ROOT, SAMPLE_CSV[database]), 'utf-8').split('\n')[0]
  return header
    .replace(/^\uFEFF/, '')
    .trim()
    .split(',')
    .map((name) => name.trim())
    .filter(Boolean)
}

function column(name: string, category?: string): DictColumn {
  return {
    name,
    description: name,
    symbol: '-',
    unit: '-',
    type: 'String',
    example: '',
    nullable: true,
    category
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

  it.each(DATABASES)('declares no group that never matches in %s', (database) => {
    // A rule that claims nothing is a typo: groupBy silently drops empty groups,
    // so without this the mistake would only show up as a missing group in the UI.
    const filled = new Set(Object.keys(tally(database)))
    const declared = FIELD_GROUPS[database].map((rule) => rule.id)
    expect(declared.filter((id) => !filled.has(id))).toEqual([])
  })
})

describe('fieldGroups: group sizes', () => {
  it('splits the 153 columns of connections into twelve groups', () => {
    expect(tally('connections')).toEqual({
      identification: 5,
      test_setup: 5,
      detailing: 4,
      beam: 33,
      column_member: 23,
      welds: 11,
      composite_slab: 18,
      panel_zone: 18,
      panel_zone_strength: 14,
      demand: 15,
      response: 3,
      provenance: 4
    })
  })

  it('splits the 25 columns of residual stresses into six groups', () => {
    expect(tally('residuals')).toEqual({
      identification: 3,
      geometry: 9,
      material: 5,
      residual_stress: 2,
      provenance: 4,
      internal: 2
    })
  })

  it('keeps every database under a scannable number of groups', () => {
    DATABASES.forEach((database) => {
      expect(FIELD_GROUPS[database].length).toBeLessThanOrEqual(12)
    })
  })
})

describe('fieldGroups: element symbols never leak across databases', () => {
  // The chemistry rule is only reachable from the material databases. Applied
  // globally it would swallow real structural variables that happen to be spelled
  // like an element.
  it('reads b as boron in a coupon and as the section width elsewhere', () => {
    expect(groupFor('tensile', column('b'))).toBe('chemistry')
    expect(groupFor('cyclic', column('b'))).toBe('chemistry')
    expect(groupFor('residuals', column('b'))).toBe('geometry')
  })

  it('reads h as hydrogen in a coupon and as the section height elsewhere', () => {
    expect(groupFor('cyclic', column('h'))).toBe('chemistry')
    expect(groupFor('residuals', column('h'))).toBe('geometry')
  })

  it('reads p as phosphorus in a coupon and as the axial load in columns', () => {
    expect(groupFor('tensile', column('p'))).toBe('chemistry')
    expect(groupFor('columns', column('p'))).toBe('loading')
  })
})

describe('fieldGroups: name-driven rules', () => {
  it('groups the two HSS backbone calibrations separately', () => {
    expect(groupFor('hss', column('theta_p_pos_100fit__rad'))).toBe('backbone_100fit')
    expect(groupFor('hss', column('mc_my_neg_80fit'))).toBe('backbone_80fit')
  })

  it('picks up a new prefixed column with no rule change', () => {
    expect(groupFor('cyclic', column('uvc_rho_new'))).toBe('model_parameters')
    expect(groupFor('ductile-fracture', column('swdfm_gamma'))).toBe('model_parameters')
    expect(groupFor('tensile', column('pid_torque_p'))).toBe('instrumentation')
  })

  it('matches regardless of the casing the dictionary uses', () => {
    expect(groupFor('braces', column('specimen_ID'))).toBe('identification')
    expect(groupFor('ductile-fracture', column('chemical_composition_Mn'))).toBe('chemistry')
    expect(groupFor('residuals', column('A'))).toBe('geometry')
  })

  it('separates nominal from measured geometry', () => {
    expect(groupFor('ebf', column('h_n'))).toBe('geometry')
    expect(groupFor('ebf', column('h_m'))).toBe('geometry_measured')
    expect(groupFor('ductile-fracture', column('nom_notch_width'))).toBe('geometry')
    expect(groupFor('ductile-fracture', column('meas_notch_width'))).toBe('geometry_measured')
  })
})

describe('fieldGroups: dictionary override', () => {
  it('prefers a category carried by the data dictionary', () => {
    expect(groupFor('residuals', column('b', 'material'))).toBe('material')
  })

  it('falls back to the rules for a category it does not know', () => {
    expect(groupFor('residuals', column('b', 'not_a_group'))).toBe('geometry')
  })
})

describe('fieldGroups: groupBy', () => {
  const items = ['reference', 'id', 'sigma_0_f', 'date'].map((name) => column(name))

  it('returns groups in rule order, not in input order', () => {
    expect(groupBy('residuals', items, (item) => item).map((group) => group.id)).toEqual([
      'identification',
      'residual_stress',
      'provenance'
    ])
  })

  it('keeps the members of a group in input order', () => {
    const identification = groupBy('residuals', items, (item) => item)[0]
    expect(identification.items.map((item) => item.name)).toEqual(['id', 'date'])
  })

  it('drops groups nothing landed in', () => {
    const ids = groupBy('residuals', items, (item) => item).map((group) => group.id)
    expect(ids).not.toContain('geometry')
  })

  it('sends an unclaimed column to the catch-all, last', () => {
    const groups = groupBy('residuals', [column('brand_new_column')], (item) => item)
    expect(groups).toEqual([{ id: 'other', items: [column('brand_new_column')] }])
  })
})

describe('fieldGroups: groupOrder', () => {
  it('ends with the catch-all so an unclaimed column never jumps the list', () => {
    const order: FieldGroupId[] = groupOrder('braces')
    expect(order[0]).toBe('identification')
    expect(order[order.length - 1]).toBe('other')
  })
})

describe('fieldGroups: ratios land where a reader looks for them', () => {
  // `_over_` alone is not enough of a signal: a columns test reports both
  // geometric slenderness ratios and axial load ratios in the same notation.
  it('separates slenderness ratios from axial load ratios', () => {
    expect(groupFor('columns', column('h_over_t_cw'))).toBe('slenderness')
    expect(groupFor('columns', column('l_b_over_r_yc'))).toBe('slenderness')
    expect(groupFor('columns', column('p_g_over_p_ym'))).toBe('loading')
    expect(groupFor('columns', column('p_c_over_p_yn'))).toBe('capacity')
  })
})
