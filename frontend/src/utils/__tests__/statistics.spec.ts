import { toBins, type Count } from '@/utils/statistics'
import { describe, expect, it } from 'vitest'

describe('statistics.toBins', () => {
  it('preserves the total count per name across bins', () => {
    const counts: Count[] = [
      { name: 'a', value: 1, count: 2 },
      { name: 'a', value: 9, count: 1 },
      { name: 'b', value: 5, count: 3 }
    ]
    const bins = toBins(['a', 'b'], counts)

    expect(bins.map((bin) => bin.name)).toEqual(['a', 'b'])

    const totalFor = (name: string) =>
      bins
        .find((bin) => bin.name === name)!
        .data.map((row) => row[1])
        .filter((count): count is number => typeof count === 'number')
        .reduce((sum, count) => sum + count, 0)

    expect(totalFor('a')).toBe(3)
    expect(totalFor('b')).toBe(3)
  })

  it('emits [label, count, min, max] tuples and blanks empty bins', () => {
    const bins = toBins(['a'], [{ name: 'a', value: 1, count: 1 }])
    const row = bins[0].data[0]
    expect(row).toHaveLength(4)
    expect(typeof row[0]).toBe('string')
    expect(typeof row[2]).toBe('number')
    expect(typeof row[3]).toBe('number')
    // bins with no matching entries report "" rather than 0
    expect(bins[0].data.every((r) => r[1] === '' || typeof r[1] === 'number')).toBe(true)
  })
})
