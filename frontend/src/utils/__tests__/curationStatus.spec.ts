import {
  STATUS_COLUMN,
  VERIFIED_ONLY_SEARCH,
  idsSearch,
  isUnverified
} from '@/utils/curationStatus'
import { queryKeyValueSeparator } from '@/composables/dashboard'
import { compileQuery, inferFieldTypes, type Row } from '@/utils/queryEngine'
import { describe, expect, it } from 'vitest'

const rows: Row[] = [
  { id: 'B1', data_curation_status: 'verified' },
  { id: 'B10', data_curation_status: 'unverified' },
  { id: 'B2', data_curation_status: 'unverified' }
]
const types = inferFieldTypes(rows)
const keep = (key: string, search: string) =>
  rows.filter(compileQuery(`${key}${queryKeyValueSeparator}${search}`, types)).map((row) => row.id)

describe('isUnverified', () => {
  it('flags only the unverified rows', () => {
    expect(rows.map(isUnverified)).toEqual([false, true, true])
  })

  it('reads a row without the column as verified', () => {
    expect(isUnverified({ id: 'B1' })).toBe(false)
    expect(isUnverified(null)).toBe(false)
  })
})

describe('the dashboard searches', () => {
  it('"Verified only" keeps the verified rows, an exact match', () => {
    // "verified" is inside "unverified", so a plain substring would keep all.
    expect(keep(STATUS_COLUMN, VERIFIED_ONLY_SEARCH)).toEqual(['B1'])
  })

  it('one id is an exact match, so B1 does not keep B10', () => {
    expect(keep('id', idsSearch(['B1']))).toEqual(['B1'])
  })

  it('several ids keep exactly those rows', () => {
    expect(keep('id', idsSearch(['B1', 'B2']))).toEqual(['B1', 'B2'])
  })
})
