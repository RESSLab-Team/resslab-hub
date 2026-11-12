import type { DictColumn, DictType } from '@/stores/dictionary'
import {
  CATEGORICAL_MAX_DISTINCT,
  profileColumns,
  visibleFilters,
  type FilterDescriptor
} from '@/utils/filterProfile'
import type { Row } from '@/utils/queryEngine'
import { describe, expect, it } from 'vitest'

function column(name: string, type: DictType = 'String'): DictColumn {
  return { name, description: name, symbol: '-', unit: '-', type, example: '', nullable: true }
}

/** Profile a single column against the values it takes, row by row. */
function profileOne(name: string, type: DictType, values: unknown[]): FilterDescriptor {
  const rows: Row[] = values.map((value, index) => ({ id: String(index), [name]: value }))
  return profileColumns(rows, [column(name, type)])[0]
}

describe('filterProfile: dictionary type dispatch', () => {
  it('classifies booleans, dates and numbers from the dictionary type', () => {
    expect(profileOne('slab', 'Boolean', [true, false, true]).kind).toBe('boolean')
    expect(profileOne('date', 'Date', ['2001-01-01', '2010-06-02']).kind).toBe('date')
    expect(profileOne('d_b', 'DecimalFloat', [1.5, 2.5, 3.5]).kind).toBe('numeric')
    expect(profileOne('n_bolts', 'SmallInteger', [2, 4, 6]).kind).toBe('numeric')
  })

  it('trusts the dictionary over the data: a String date stays a text/categorical column', () => {
    // tensile_coupons.date is typed String while `year` is numeric — it must not
    // become a date brush just because the values parse as dates.
    const dates = Array.from({ length: 40 }, (_, i) => `2020-01-${String((i % 28) + 1)}`)
    expect(profileOne('date', 'String', dates).kind).not.toBe('date')
  })

  it('reports boolean option counts including the missing bucket', () => {
    const descriptor = profileOne('slab', 'Boolean', [true, true, false, null])
    expect(descriptor.options).toEqual([
      { value: 'True', count: 2 },
      { value: 'False', count: 1 },
      { value: 'NA', count: 1 }
    ])
  })

  it('offers not reported and not applicable as two options (#427)', () => {
    const rows: Row[] = [
      { id: '1', slab: true, not_reported: [] },
      { id: '2', slab: null, not_reported: ['slab'] },
      { id: '3', slab: null, not_reported: ['slab'] },
      { id: '4', slab: null, not_reported: [] }
    ]
    const descriptor = profileColumns(rows, [column('slab', 'Boolean')])[0]
    expect(descriptor.options).toEqual([
      { value: 'True', count: 1 },
      { value: 'NR', count: 2 },
      { value: 'NA', count: 1 }
    ])
    expect(descriptor.notReported).toBe(2)
    expect(descriptor.notApplicable).toBe(1)
    expect(descriptor.missing).toBe(3)
  })

  it('exposes ISO bounds for date columns', () => {
    const descriptor = profileOne('date', 'Date', ['2010-06-02', '2001-01-01', '2005-03-04'])
    expect(descriptor.dateMin).toBe('2001-01-01')
    expect(descriptor.dateMax).toBe('2010-06-02')
  })
})

describe('filterProfile: string classification', () => {
  /** n rows drawn from `domain`, cycling so every value repeats. */
  function repeated(domain: string[], n: number): string[] {
    return Array.from({ length: n }, (_, i) => domain[i % domain.length])
  }

  it('makes a short repeated domain categorical, most frequent first', () => {
    const values = ['RBS', 'RBS', 'RBS', 'WUF-W', 'WUF-W', 'BFP']
    const descriptor = profileOne('connection_type', 'String', values)
    expect(descriptor.kind).toBe('categorical')
    expect(descriptor.options).toEqual([
      { value: 'RBS', count: 3 },
      { value: 'WUF-W', count: 2 },
      { value: 'BFP', count: 1 }
    ])
  })

  it('appends the missing bucket last, after the least frequent value', () => {
    const values = [...repeated(['A992', 'A992', 'A36'], 24), null, null, null]
    const descriptor = profileOne('steel', 'String', values)
    expect(descriptor.options?.map((option) => option.value)).toEqual(['A992', 'A36', 'NA'])
    expect(descriptor.missing).toBe(3)
    expect(descriptor.nonNull).toBe(24)
  })

  it('stays categorical at exactly the distinct-count threshold', () => {
    const domain = Array.from({ length: CATEGORICAL_MAX_DISTINCT }, (_, i) => `v${i}`)
    // 4× the domain, so the ratio rule is comfortably satisfied.
    expect(profileOne('grade', 'String', repeated(domain, domain.length * 4)).kind).toBe(
      'categorical'
    )
  })

  it('falls back to text one value past the threshold', () => {
    const domain = Array.from({ length: CATEGORICAL_MAX_DISTINCT + 1 }, (_, i) => `v${i}`)
    expect(profileOne('grade', 'String', repeated(domain, domain.length * 4)).kind).toBe('text')
  })

  it('falls back to text when values barely repeat, even under the count limit', () => {
    // 10 distinct over 14 filled rows: within the count limit, but past the 50%
    // ratio, so it is an open vocabulary rather than a domain to pick from.
    const domain = Array.from({ length: CATEGORICAL_MAX_DISTINCT }, (_, i) => `v${i}`)
    const values = [...domain, ...domain.slice(0, 4)]
    expect(profileOne('label', 'String', values).kind).toBe('text')
  })

  it('hides near-unique identity columns once there are enough rows', () => {
    const ids = Array.from({ length: 40 }, (_, i) => `SPEC-${i}`)
    const descriptor = profileOne('specimen_designation', 'String', ids)
    expect(descriptor.kind).toBe('hidden')
    expect(descriptor.hiddenReason).toBe('unique')
  })

  it('keeps a near-unique column as text while the sample is still small', () => {
    const ids = Array.from({ length: 6 }, (_, i) => `SPEC-${i}`)
    expect(profileOne('specimen_designation', 'String', ids).kind).toBe('text')
  })

  it('hides link columns by their values', () => {
    const links = Array.from({ length: 8 }, (_, i) => `https://doi.org/10.100/${i}`)
    const descriptor = profileOne('publication', 'String', links)
    expect(descriptor.hiddenReason).toBe('url')
  })

  it('hides identity/link columns by name whatever they contain', () => {
    expect(profileOne('id', 'String', ['a', 'a', 'b']).hiddenReason).toBe('denylist')
    expect(profileOne('brace_id', 'String', ['a', 'a', 'b']).hiddenReason).toBe('denylist')
    expect(profileOne('link', 'String', ['a', 'a', 'b']).hiddenReason).toBe('denylist')
  })

  it('hides the map coordinates, which every database carries', () => {
    // Numeric and well-spread, so only the name can rule them out — they locate
    // a specimen on the overview map rather than describing the test.
    expect(profileOne('latitude', 'DecimalFloat', [46.5, 47.1, 48.3]).hiddenReason).toBe('denylist')
    expect(profileOne('longitude', 'DecimalFloat', [6.5, 7.1, 8.3]).hiddenReason).toBe('denylist')
  })

  it('demotes a categorical column whose values carry a query separator', () => {
    // `,` separates set members and `;` separates clauses, so such a value could
    // never round-trip as a filter value.
    const values = ['Demo, et al.', 'Demo, et al.', 'Other', 'Other']
    const descriptor = profileOne('reference', 'String', values)
    expect(descriptor.kind).toBe('text')
    expect(descriptor.demoted).toBe(true)
  })

  it('treats the measurement-bearing String columns as text search', () => {
    // Braces `l_1t` & friends are typed String but hold mixed measurements.
    const values = Array.from({ length: 30 }, (_, i) => String(100 + i))
    expect(profileOne('l_1t', 'String', values).kind).toBe('hidden')
    const mixed = ['Demo value', ...Array.from({ length: 10 }, (_, i) => String(100 + i))]
    expect(profileOne('l_1t', 'String', mixed).kind).toBe('text')
  })
})

describe('filterProfile: numeric histograms', () => {
  it('exposes bounds, bins and matching edges', () => {
    const values = Array.from({ length: 50 }, (_, i) => i)
    const descriptor = profileOne('kl_r', 'DecimalFloat', values)
    expect(descriptor.min).toBe(0)
    expect(descriptor.max).toBe(49)
    expect(descriptor.bins?.length).toBeGreaterThan(1)
    // Edges are the first bin's left edge then every bin's right edge.
    expect(descriptor.binEdges).toHaveLength((descriptor.bins?.length ?? 0) + 1)
    expect(descriptor.binEdges?.[0]).toBe(descriptor.bins?.[0][2])
  })

  it('bin counts add up to the number of filled rows', () => {
    const values = [1, 1, 2, 3, 5, 8, 13, null, 21]
    const descriptor = profileOne('d_br', 'DecimalFloat', values)
    const total = (descriptor.bins ?? []).reduce(
      (sum, bin) => sum + (typeof bin[1] === 'number' ? bin[1] : 0),
      0
    )
    expect(total).toBe(8)
    expect(descriptor.missing).toBe(1)
  })

  it('hides a constant numeric column — nothing to filter on', () => {
    const descriptor = profileOne('t_w', 'DecimalFloat', [7, 7, 7, 7])
    expect(descriptor.kind).toBe('hidden')
    expect(descriptor.hiddenReason).toBe('constant')
  })
})

describe('filterProfile: dataset-level behaviour', () => {
  const rows: Row[] = [
    { id: '1', steel: 'A992', kl_r: 40, slab: true, notes: 'a' },
    { id: '2', steel: 'A992', kl_r: 60, slab: false, notes: 'b' },
    { id: '3', steel: 'A36', kl_r: 80, slab: true, notes: 'c' }
  ]
  const columns = [
    column('id'),
    column('steel'),
    column('kl_r', 'DecimalFloat'),
    column('slab', 'Boolean'),
    column('absent', 'DecimalFloat')
  ]

  it('preserves dictionary order and returns one descriptor per column', () => {
    const profile = profileColumns(rows, columns)
    expect(profile.map((descriptor) => descriptor.key)).toEqual([
      'id',
      'steel',
      'kl_r',
      'slab',
      'absent'
    ])
  })

  it('hides dictionary columns the rows do not carry', () => {
    const profile = profileColumns(rows, columns)
    expect(profile[4].hiddenReason).toBe('missing')
  })

  it('visibleFilters drops every hidden column', () => {
    const visible = visibleFilters(profileColumns(rows, columns))
    expect(visible.map((descriptor) => descriptor.key)).toEqual(['steel', 'kl_r', 'slab'])
  })

  it('handles an empty dataset without throwing', () => {
    const profile = profileColumns([], columns)
    expect(profile.every((descriptor) => descriptor.kind === 'hidden')).toBe(true)
  })
})
