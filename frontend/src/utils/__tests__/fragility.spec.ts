import { fragilityCurve, univariateOption } from '@/utils/fragility'
import { describe, expect, it } from 'vitest'

describe('fragility.fragilityCurve', () => {
  it('is a lognormal CDF: starts at 0 and crosses 0.5 at the median', () => {
    const median = 1
    const sigma = 0.4
    const curve = fragilityCurve(median, sigma, median, 2)

    // sdr = range(0, 2, 0.01) -> 200 points starting at 0
    expect(curve.length).toBe(200)
    expect(curve[0]).toEqual([0, 0])

    // value == median (index 100, sdr = 1.00) -> CDF = 0.5
    expect(curve[100][0]).toBeCloseTo(1, 10)
    expect(curve[100][1]).toBeCloseTo(0.5, 6)
  })

  it('is monotonically non-decreasing', () => {
    const curve = fragilityCurve(1.5, 0.3, 1.5, 3)
    for (let i = 1; i < curve.length; i++) {
      expect(curve[i][1]).toBeGreaterThanOrEqual(curve[i - 1][1])
    }
  })
})

describe('fragility.univariateOption', () => {
  it('produces one line series per damage state with DS labels', () => {
    const option = univariateOption(
      [
        { median: 1, beta: 0.4 },
        { median: 2, beta: 0.3 }
      ],
      3
    )
    const series = option.series as Array<{ name: string; type: string; data: unknown[] }>
    expect(series).toHaveLength(2)
    expect(series.map((s) => s.name)).toEqual(['DS1', 'DS2'])
    expect(series.every((s) => s.type === 'line' && s.data.length > 0)).toBe(true)
  })
})
