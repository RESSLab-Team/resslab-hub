import { describe, expect, it } from 'vitest'
import { computeWindow, DISABLE_BELOW, OVERSCAN, ROW_HEIGHT } from '../useVirtualRows'

describe('computeWindow', () => {
  it('renders everything when the row count is at or below the disable threshold', () => {
    const total = DISABLE_BELOW
    expect(computeWindow(0, 500, total)).toEqual({
      startIndex: 0,
      endIndex: total,
      padTop: 0,
      padBottom: 0
    })
  })

  it('renders everything when the viewport has not been measured yet', () => {
    const total = 1000
    expect(computeWindow(0, 0, total)).toEqual({
      startIndex: 0,
      endIndex: total,
      padTop: 0,
      padBottom: 0
    })
  })

  it('windows to the visible slice plus overscan at the top', () => {
    const total = 1000
    const viewport = 10 * ROW_HEIGHT // 10 rows visible
    const w = computeWindow(0, viewport, total)
    expect(w.startIndex).toBe(0) // clamped, no rows above
    expect(w.endIndex).toBe(10 + OVERSCAN) // visible + overscan below
    expect(w.padTop).toBe(0)
    expect(w.padBottom).toBe((total - w.endIndex) * ROW_HEIGHT)
  })

  it('windows around a mid-list scroll offset with overscan both sides', () => {
    const total = 1000
    const viewport = 10 * ROW_HEIGHT
    const scrollTop = 100 * ROW_HEIGHT // first visible row is index 100
    const w = computeWindow(scrollTop, viewport, total)
    expect(w.startIndex).toBe(100 - OVERSCAN)
    expect(w.endIndex).toBe(100 + 10 + OVERSCAN)
    expect(w.padTop).toBe((100 - OVERSCAN) * ROW_HEIGHT)
    expect(w.padBottom).toBe((total - (110 + OVERSCAN)) * ROW_HEIGHT)
  })

  it('clamps the end index at the last row near the bottom', () => {
    const total = 1000
    const viewport = 10 * ROW_HEIGHT
    const scrollTop = 995 * ROW_HEIGHT
    const w = computeWindow(scrollTop, viewport, total)
    expect(w.endIndex).toBe(total)
    expect(w.padBottom).toBe(0)
  })

  it('pad heights always sum with rendered rows to the full page height', () => {
    const total = 500
    const viewport = 12 * ROW_HEIGHT
    const w = computeWindow(37 * ROW_HEIGHT, viewport, total)
    const renderedHeight = (w.endIndex - w.startIndex) * ROW_HEIGHT
    expect(w.padTop + renderedHeight + w.padBottom).toBe(total * ROW_HEIGHT)
  })
})
