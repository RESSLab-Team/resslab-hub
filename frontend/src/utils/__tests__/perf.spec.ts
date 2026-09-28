import { PERF_PREFIX, perfMark, perfMeasure } from '@/utils/perf'
import { afterEach, describe, expect, it, vi } from 'vitest'

/**
 * These marks sit on the hot path of the dashboard: one per ECharts repaint,
 * so one per chart per drag frame. They must never throw and never depend on
 * the User Timing API being there, which jsdom's is only partly.
 */
describe('perfMark', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('prefixes every name so the benchmark can pick ours out of the buffer', () => {
    const mark = vi.spyOn(performance, 'mark')
    perfMark('chart:render')
    expect(mark).toHaveBeenCalledWith(`${PERF_PREFIX}chart:render`, undefined)
  })

  it('passes the detail through for the harness to read back', () => {
    const mark = vi.spyOn(performance, 'mark')
    perfMark('dataset:fetch:end', { rows: 10000 })
    expect(mark).toHaveBeenCalledWith(`${PERF_PREFIX}dataset:fetch:end`, {
      detail: { rows: 10000 }
    })
  })

  it('swallows a failing mark rather than breaking the dashboard', () => {
    vi.spyOn(performance, 'mark').mockImplementation(() => {
      throw new Error('buffer full')
    })
    expect(() => perfMark('chart:render')).not.toThrow()
  })
})

describe('perfMeasure', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('measures between two of our own marks', () => {
    const measure = vi.spyOn(performance, 'measure')
    perfMeasure('dataset:fetch', 'dataset:fetch:start', 'dataset:fetch:end')
    expect(measure).toHaveBeenCalledWith(`${PERF_PREFIX}dataset:fetch`, {
      start: `${PERF_PREFIX}dataset:fetch:start`,
      end: `${PERF_PREFIX}dataset:fetch:end`
    })
  })

  it('measures up to now when no end mark is given', () => {
    const measure = vi.spyOn(performance, 'measure')
    perfMeasure('brush:live', 'brush:live:start')
    expect(measure).toHaveBeenCalledWith(`${PERF_PREFIX}brush:live`, {
      start: `${PERF_PREFIX}brush:live:start`
    })
  })

  it('swallows a missing start mark', () => {
    vi.spyOn(performance, 'measure').mockImplementation(() => {
      throw new Error('mark not found')
    })
    expect(() => perfMeasure('brush:live', 'never:marked')).not.toThrow()
  })
})
