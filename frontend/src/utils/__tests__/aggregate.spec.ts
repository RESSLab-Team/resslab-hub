import { counts, dateRange, matrix, range, totalCount } from '@/utils/aggregate'
import type { Row } from '@/utils/queryEngine'
import { describe, expect, it } from 'vitest'

const rows: Row[] = [
  { id: '1', connection_type: 'WUF-W', slab: true, t_dp: 10, date: '2005-01-01' },
  { id: '2', connection_type: 'RBS', slab: false, t_dp: 0, date: '2010-06-01' },
  { id: '3', connection_type: 'WUF-W', slab: true, t_dp: 5, date: '1998-03-01' },
  { id: '4', connection_type: null, slab: false, t_dp: Number.NaN, date: '2001-01-01' }
]

describe('aggregate.counts', () => {
  it('groups by a single field, formatting keys like the backend', () => {
    expect(counts(rows, ['connection_type'])).toEqual([
      { names: ['WUF-W'], value: 2 },
      { names: ['RBS'], value: 1 },
      { names: ['NA'], value: 1 }
    ])
  })

  it('groups by two fields with Python-style boolean labels', () => {
    expect(counts(rows, ['slab', 'connection_type'])).toEqual([
      { names: ['True', 'WUF-W'], value: 2 },
      { names: ['False', 'RBS'], value: 1 },
      { names: ['False', 'NA'], value: 1 }
    ])
  })
})

describe('aggregate.totalCount', () => {
  it('reports the row count as a single empty-named group', () => {
    expect(totalCount(rows)).toEqual([{ names: [], value: 4 }])
  })
})

describe('aggregate.range', () => {
  it('returns min/max ignoring null and NaN', () => {
    expect(range(rows, 't_dp')).toEqual({ min: 0, max: 10 })
  })
})

describe('aggregate.dateRange', () => {
  it('returns lexicographic min/max of ISO dates', () => {
    expect(dateRange(rows, 'date')).toEqual({ min: '1998-03-01', max: '2010-06-01' })
  })
})

describe('aggregate.matrix', () => {
  it('projects id + fields per row, collapsing NaN to null', () => {
    expect(matrix(rows, 'id', ['connection_type', 't_dp'])).toEqual({
      ids: ['1', '2', '3', '4'],
      data: [
        ['WUF-W', 10],
        ['RBS', 0],
        ['WUF-W', 5],
        [null, null]
      ]
    })
  })

  it('returns the identical model for a repeated call', () => {
    const fields = ['connection_type', 't_dp']
    const first = matrix(rows, 'id', fields)
    expect(matrix(rows, 'id', fields)).toBe(first)
  })

  // A drag re-projects overlapping subsets frame after frame; the row tuples are
  // reused so only the two outer arrays are allocated.
  it('reuses the per-row tuples across different row subsets', () => {
    const fields = ['connection_type', 't_dp']
    const all = matrix(rows, 'id', fields)
    const subset = matrix(rows.slice(1, 3), 'id', fields)
    expect(subset.data[0]).toBe(all.data[1])
    expect(subset.data[1]).toBe(all.data[2])
    expect(subset).toEqual({
      ids: ['2', '3'],
      data: [
        ['RBS', 0],
        ['WUF-W', 5]
      ]
    })
  })

  it('rebuilds tuples when the field list or id field changes', () => {
    const first = matrix(rows, 'id', ['connection_type', 't_dp'])
    const narrowed = matrix(rows, 'id', ['t_dp'])
    expect(narrowed.data[0]).not.toBe(first.data[0])
    expect(narrowed.data).toEqual([[10], [0], [5], [null]])
    const rekeyed = matrix(rows, 'connection_type', ['t_dp'])
    expect(rekeyed.ids).toEqual(['WUF-W', 'RBS', 'WUF-W', 'null'])
  })
})

describe('aggregate edge cases', () => {
  it('handles an empty row array', () => {
    expect(counts([], ['connection_type'])).toEqual([])
    expect(totalCount([])).toEqual([{ names: [], value: 0 }])
    expect(range([], 't_dp')).toEqual({ min: 0, max: 0 })
    expect(dateRange([], 'date')).toEqual({ min: '', max: '' })
    expect(matrix([], 'id', ['t_dp'])).toEqual({ ids: [], data: [] })
  })

  it('groups all-null fields under NA', () => {
    const nullRows: Row[] = [
      { id: '1', type: null },
      { id: '2', type: null }
    ]
    expect(counts(nullRows, ['type'])).toEqual([{ names: ['NA'], value: 2 }])
  })
})
