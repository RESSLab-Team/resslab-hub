import type { CurationDetail } from '@/backend'
import { requestFieldsFor } from '@/components/curation/ghost'
import { cellValue, databaseIdForType, isMissing, toExperimentRows } from '@/utils/curation'
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
