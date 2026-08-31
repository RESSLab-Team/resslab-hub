import type { CurationDetail } from '@/backend'
import { CURVE_SOURCES } from '@/components/curation/curves'
import {
  cohortQueryFor,
  GHOST_CONFIGS,
  isEmptyBrush,
  mergeBrush,
  requestFieldsFor
} from '@/components/curation/ghost'
import { cellValue, databaseIdForType, isMissing, toExperimentRows } from '@/utils/curation'
import type { DatabaseId } from '@/utils/navigation'
import { timeSeriesKindsFor } from '@/utils/timeseries'
import { describe, expect, it } from 'vitest'

describe('databaseIdForType', () => {
  it('inverts the contribution database map', () => {
    expect(databaseIdForType('all-braces')).toBe('braces')
    expect(databaseIdForType('all-hss-columns')).toBe('hss')
    expect(databaseIdForType('all-material')).toBe('cyclic')
    expect(databaseIdForType('not-a-type')).toBeNull()
  })
})

describe('toExperimentRows', () => {
  it('indexes experiments so validation row N maps to uid N-1', () => {
    const detail = {
      experiments: [
        { id: 'B9', cells: { id: 'B9', f_y: '400' } },
        { id: 'B10', cells: { id: 'B10', f_y: 'NR' } }
      ]
    } as unknown as CurationDetail
    const rows = toExperimentRows(detail)
    expect(rows).toHaveLength(2)
    expect(rows[0]).toEqual({ uid: 0, cells: { id: 'B9', f_y: '400' } })
    expect(rows[1].uid).toBe(1)
  })
})

describe('cell helpers', () => {
  it('parses numbers, keeps strings, and nulls the NR sentinel', () => {
    expect(cellValue('400')).toBe(400)
    expect(cellValue('-1.5')).toBe(-1.5)
    expect(cellValue('HSS Square')).toBe('HSS Square')
    expect(cellValue('NR')).toBeNull()
    expect(cellValue('  ')).toBeNull()
    expect(cellValue(undefined)).toBeNull()
  })

  it('flags blank and NR cells as missing', () => {
    expect(isMissing('NR')).toBe(true)
    expect(isMissing('')).toBe(true)
    expect(isMissing('400')).toBe(false)
  })
})

describe('requestFieldsFor', () => {
  it('expands division axes and dedupes', () => {
    const fields = [{ id: 'kl_r' }, { id: { dividend: 'd_br', divisor: 't_br' } }, { id: 'kl_r' }]
    expect(requestFieldsFor(fields)).toEqual(['kl_r', 'd_br', 't_br'])
  })
})

describe('cohortQueryFor', () => {
  const cells = { steel: 'S355', shape: 'HSS Square', protocol: 'NR', size: '' }

  it('ANDs one exact-match clause per selected field', () => {
    // The trailing comma is what makes it exact: 'S355' must not match 'S355J2'.
    expect(cohortQueryFor(cells, ['steel', 'shape'])).toBe('steel:S355,;shape:HSS Square,')
  })

  it('skips fields the specimen does not report', () => {
    expect(cohortQueryFor(cells, ['steel', 'protocol', 'size'])).toBe('steel:S355,')
  })

  it('is undefined when nothing is selectable, so the cohort is the whole database', () => {
    expect(cohortQueryFor(cells, [])).toBeUndefined()
    expect(cohortQueryFor(cells, ['protocol'])).toBeUndefined()
  })
})

describe('isEmptyBrush', () => {
  it('treats a cleared brush as no selection', () => {
    expect(isEmptyBrush(null)).toBe(true)
    expect(isEmptyBrush(undefined)).toBe(true)
    expect(isEmptyBrush({ clauses: {} })).toBe(true)
    expect(isEmptyBrush({ ids: [] })).toBe(true)
  })

  it('recognises a real selection', () => {
    expect(isEmptyBrush({ clauses: { f_y: '300<<400' } })).toBe(false)
    expect(isEmptyBrush({ ids: ['B1'] })).toBe(false)
  })
})

describe('mergeBrush', () => {
  const criteria = 'steel:S355,;shape:HSS Square,'

  it('leaves the criteria query untouched without a selection', () => {
    expect(mergeBrush(criteria, null)).toBe(criteria)
    expect(mergeBrush(criteria, { clauses: {} })).toBe(criteria)
    expect(mergeBrush(criteria, { ids: [] })).toBe(criteria)
  })

  it('splices a brushed numeric range in beside the criteria', () => {
    expect(mergeBrush(criteria, { clauses: { f_y: '300<<400' } })).toBe(`${criteria};f_y:300<<400`)
  })

  it('makes a single brushed category exact, so S355 does not keep S355J2', () => {
    expect(mergeBrush(undefined, { clauses: { steel: 'S355' } })).toBe('steel:S355,')
  })

  it('leaves a multi-value category set alone — it already matches exactly', () => {
    expect(mergeBrush(undefined, { clauses: { steel: 'S355,S690' } })).toBe('steel:S355,S690')
  })

  it('maps the derived-axis id fallback onto an exact id clause', () => {
    expect(mergeBrush(undefined, { ids: ['B1'] })).toBe('id:B1,')
    expect(mergeBrush(undefined, { ids: ['B1', 'B2'] })).toBe('id:B1,B2')
  })

  it('replaces the criterion on a field the curator then brushed', () => {
    expect(mergeBrush(criteria, { clauses: { steel: 'S460' } })).toBe(
      'shape:HSS Square,;steel:S460,'
    )
  })

  it('builds a query from scratch when no criteria are active', () => {
    expect(mergeBrush(undefined, { clauses: { f_y: '300<<400' } })).toBe('f_y:300<<400')
  })
})

describe('cohort candidates', () => {
  it('pre-selects a subset of the offered criteria', () => {
    for (const [database, config] of Object.entries(GHOST_CONFIGS)) {
      expect(config.cohortCandidates.length, database).toBeGreaterThan(0)
      for (const field of config.cohortDefaults) {
        expect(config.cohortCandidates, `${database}/${field}`).toContain(field)
      }
    }
  })
})

describe('CURVE_SOURCES', () => {
  it('keys every source by a real time-series kind of that database', () => {
    for (const [database, sources] of Object.entries(CURVE_SOURCES)) {
      const keys = timeSeriesKindsFor(database as DatabaseId).map((kind) => kind.key)
      for (const key of Object.keys(sources)) {
        expect(keys, `${database}/${key}`).toContain(key)
      }
    }
  })

  it('swaps the cyclic-coupon columns so strain is plotted on x', () => {
    const transform = CURVE_SOURCES.cyclic?.stress_strain.transform
    expect(transform?.([[400, 0.002]])).toEqual([[0.002, 400]])
  })
})
