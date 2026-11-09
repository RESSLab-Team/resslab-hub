import type { DictColumn, DictType } from '@/stores/dictionary'
import { liveBins, liveCounts, liveOptions, staticCounts } from '@/utils/filterCounts'
import { profileColumns, type FilterDescriptor } from '@/utils/filterProfile'
import type { Row } from '@/utils/queryEngine'
import { describe, expect, it } from 'vitest'

function column(name: string, type: DictType): DictColumn {
  return { name, description: name, symbol: '-', unit: '-', type, example: '', nullable: true }
}

function profileOne(rows: Row[], name: string, type: DictType): FilterDescriptor {
  return profileColumns(rows, [column(name, type)])[0]
}

const CATEGORY_ROWS: Row[] = [
  ...Array.from({ length: 5 }, () => ({ type: 'RBS' })),
  ...Array.from({ length: 3 }, () => ({ type: 'WUF-W' })),
  { type: null },
  { type: null }
]

describe('liveOptions', () => {
  const filter = profileOne(CATEGORY_ROWS, 'type', 'String')

  it('gives the static counts back over every row', () => {
    expect(filter.kind).toBe('categorical')
    expect(liveOptions(CATEGORY_ROWS, filter)).toEqual(
      filter.options!.map((option) => ({ ...option, total: option.count }))
    )
  })

  it('keeps the static order when the ranking changes', () => {
    const rows = [{ type: 'WUF-W' }, { type: 'WUF-W' }, { type: 'RBS' }]
    expect(liveOptions(rows, filter).map((option) => option.value)).toEqual(['RBS', 'WUF-W', 'NA'])
    expect(liveOptions(rows, filter)[1]).toEqual({ value: 'WUF-W', count: 2, total: 3 })
  })

  it('keeps a value with no row left, at zero', () => {
    expect(liveOptions([{ type: 'RBS' }], filter)).toEqual([
      { value: 'RBS', count: 1, total: 5 },
      { value: 'WUF-W', count: 0, total: 3 },
      { value: 'NA', count: 0, total: 2 }
    ])
  })

  it('puts null, NaN and an empty result in the right place', () => {
    const rows = [{ type: null }, { type: undefined }, { type: Number.NaN }]
    expect(liveOptions(rows, filter)[2]).toEqual({ value: 'NA', count: 3, total: 2 })
    expect(liveOptions([], filter).every((option) => option.count === 0)).toBe(true)
  })

  it('ignores a value the static list does not have', () => {
    const counted = liveOptions([{ type: 'New' }], filter)
    expect(counted.map((option) => option.value)).toEqual(['RBS', 'WUF-W', 'NA'])
    expect(counted.every((option) => option.count === 0)).toBe(true)
  })

  it('counts booleans under their formatted value', () => {
    const rows = [{ slab: true }, { slab: true }, { slab: false }]
    const boolean = profileOne(rows, 'slab', 'Boolean')
    expect(liveOptions([{ slab: false }], boolean)).toEqual([
      { value: 'True', count: 0, total: 2 },
      { value: 'False', count: 1, total: 1 }
    ])
  })
})

describe('liveBins', () => {
  const rows: Row[] = Array.from({ length: 101 }, (_, index) => ({ d: index }))
  const filter = profileOne(rows, 'd', 'Numeric')

  function heights(counted: { 1: number | string }[]): (number | string)[] {
    return counted.map((bin) => bin[1])
  }

  it('gives the static bins back over every row', () => {
    expect(filter.kind).toBe('numeric')
    expect(liveBins(rows, filter)).toEqual(filter.bins)
  })

  it('also matches toBins on decimals and repeated values', () => {
    const decimals: Row[] = [0.1, 0.1, 0.15, 0.2, 0.33, 0.33, 0.33, 0.47, 0.6].map((d) => ({ d }))
    const decimal = profileOne(decimals, 'd', 'Numeric')
    expect(liveBins(decimals, decimal)).toEqual(decimal.bins)
  })

  it('puts a value on an edge in the bin on its right, and the last edge in the last bin', () => {
    const edges = filter.binEdges!
    const counted = heights(liveBins([{ d: edges[1] }, { d: edges[edges.length - 1] }], filter))
    expect(counted[1]).toBe(1)
    expect(counted[counted.length - 1]).toBe(1)
    expect(counted.filter((height) => height !== '')).toHaveLength(2)
  })

  it('keeps the edges and skips what it cannot place', () => {
    const counted = liveBins([{ d: null }, { d: Number.NaN }, { d: 1000 }, { d: -1 }], filter)
    expect(counted.map((bin) => [bin[2], bin[3]])).toEqual(filter.bins!.map((b) => [b[2], b[3]]))
    expect(heights(counted).every((height) => height === '')).toBe(true)
  })

  it('reads a number sent as a string', () => {
    expect(heights(liveBins([{ d: '5' }], filter))[0]).toBe(1)
  })

  it('leaves a filter with no bins alone', () => {
    expect(liveBins(rows, { ...filter, bins: undefined, binEdges: undefined })).toEqual([])
  })
})

describe('liveCounts', () => {
  it('counts dates as options and keeps their chronological order', () => {
    const rows = [{ day: '2020-01-01' }, { day: '2021-01-01' }, { day: '2021-01-01' }]
    const filter = profileOne(rows, 'day', 'Date')
    expect(liveCounts([{ day: '2021-01-01' }], filter).options).toEqual([
      { value: '2020-01-01', count: 0, total: 1 },
      { value: '2021-01-01', count: 1, total: 2 }
    ])
  })

  it('leaves the shortcuts of a text filter static', () => {
    const rows: Row[] = Array.from({ length: 60 }, (_, index) => ({
      name: `Name ${index % 30}`
    }))
    const filter = profileOne(rows, 'name', 'String')
    expect(filter.kind).toBe('text')
    expect(liveCounts([], filter)).toEqual(staticCounts(filter))
  })
})
