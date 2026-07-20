import {
  compileQuery,
  filterRows,
  formatValue,
  inferFieldTypes,
  type Row
} from '@/utils/queryEngine'
import { describe, expect, it } from 'vitest'

const rows: Row[] = [
  { id: '1', connection_type: 'WUF-W', date: 2005, slab: true, t_dp: 10, section_b: 'W24' },
  { id: '2', connection_type: 'RBS', date: 2010, slab: false, t_dp: 0, section_b: 'W36' },
  { id: '3', connection_type: 'WUF-B', date: 1998, slab: true, t_dp: 5, section_b: null }
]
const types = inferFieldTypes(rows)

function ids(query: string): string[] {
  return filterRows(rows, query, types).map((row) => row.id as string)
}

describe('queryEngine.inferFieldTypes', () => {
  it('infers types from the first defined value, skipping nulls', () => {
    expect(types).toMatchObject({
      id: 'string',
      connection_type: 'string',
      date: 'number',
      slab: 'boolean',
      t_dp: 'number',
      section_b: 'string'
    })
  })
})

describe('queryEngine.filterRows', () => {
  it('returns all rows for an empty query', () => {
    expect(ids('')).toEqual(['1', '2', '3'])
  })

  it('string field: case-insensitive substring (ilike)', () => {
    expect(ids('connection_type:wuf')).toEqual(['1', '3'])
  })

  it('string field: % acts as a wildcard (e.g. option "exterior%")', () => {
    expect(ids('connection_type:WUF-%')).toEqual(['1', '3'])
  })

  it('comma → value-in-set', () => {
    expect(ids('connection_type:WUF-W,RBS')).toEqual(['1', '2'])
  })

  it('<< → inclusive numeric range', () => {
    expect(ids('date:2000<<2008')).toEqual(['1'])
    expect(ids('date:1998<<2010')).toEqual(['1', '2', '3'])
  })

  it('< and > → numeric comparison', () => {
    expect(ids('t_dp:>0')).toEqual(['1', '3'])
    expect(ids('t_dp:<5')).toEqual(['2'])
  })

  it('leading ! negates the predicate', () => {
    expect(ids('connection_type:!wuf')).toEqual(['2'])
  })

  it('number field → exact equality', () => {
    expect(ids('date:2010')).toEqual(['2'])
  })

  it('boolean field → equality', () => {
    expect(ids('slab:true')).toEqual(['1', '3'])
    expect(ids('slab:false')).toEqual(['2'])
  })

  it('global search (no colon) spans every field', () => {
    expect(ids('%W36%')).toEqual(['2'])
    expect(ids('%wuf%')).toEqual(['1', '3'])
  })

  it('negated global search', () => {
    // "no field equals exactly RBS" — true for every row (they all have other fields)
    expect(ids('!RBS')).toEqual(['1', '2', '3'])
  })

  it('; combines clauses with AND', () => {
    expect(ids('slab:true;date:2000<<2010')).toEqual(['1'])
  })
})

describe('queryEngine.formatValue', () => {
  it('matches the backend __format_value + str() output', () => {
    expect(formatValue(null)).toBe('NA')
    expect(formatValue(undefined)).toBe('NA')
    expect(formatValue(Number.NaN)).toBe('NR')
    expect(formatValue(true)).toBe('True')
    expect(formatValue(false)).toBe('False')
    expect(formatValue(2005)).toBe('2005')
    expect(formatValue(1.5)).toBe('1.5')
    expect(formatValue('WUF-W')).toBe('WUF-W')
  })
})

describe('queryEngine.compileQuery memoization', () => {
  it('returns the same predicate for a repeated (query, fieldTypes) pair', () => {
    const first = compileQuery('connection_type:WUF', types)
    const second = compileQuery('connection_type:WUF', types)
    expect(second).toBe(first)
  })

  it('recompiles when the query or the fieldTypes object changes', () => {
    const base = compileQuery('connection_type:WUF', types)
    const otherQuery = compileQuery('connection_type:RBS', types)
    expect(otherQuery).not.toBe(base)
    const otherTypes = inferFieldTypes(rows)
    const otherTypesPredicate = compileQuery('connection_type:WUF', otherTypes)
    expect(otherTypesPredicate).not.toBe(base)
  })

  it('memoized predicates filter identically to fresh compiles', () => {
    const memoized = compileQuery('date:2000<<2010', types)
    expect(rows.filter(memoized).map((row) => row.id)).toEqual(['1', '2'])
    // Reusable: a second pass over the same predicate gives the same result.
    expect(rows.filter(memoized).map((row) => row.id)).toEqual(['1', '2'])
  })
})

describe('queryEngine.filterRows memoization', () => {
  it('returns the identical array for a repeated (rows, query) pair', () => {
    const first = filterRows(rows, 'connection_type:WUF', types)
    const second = filterRows(rows, 'connection_type:WUF', types)
    expect(second).toBe(first)
    // a different query recomputes
    expect(filterRows(rows, 'connection_type:RBS', types)).not.toBe(first)
  })

  it('recomputes when the rows array identity changes', () => {
    const first = filterRows(rows, 'connection_type:WUF', types)
    const otherRows = [...rows]
    const second = filterRows(otherRows, 'connection_type:WUF', types)
    expect(second).not.toBe(first)
    expect(second).toEqual(first)
  })
})
