import type { CurationDetail } from '@/backend'
import { CURVE_SOURCES } from '@/components/curation/curves'
import { cohortQueryFor, GHOST_CONFIGS, requestFieldsFor } from '@/components/curation/ghost'
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
