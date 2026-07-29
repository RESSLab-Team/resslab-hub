import { describe, expect, it } from 'vitest'
import {
  CAP_NUMBER,
  CELL_PAD,
  distributeWidths,
  HEADER_CHROME,
  IDEAL_FLOOR,
  LAST_COL_EXTRA,
  measureColumnIdeals,
  SELECT_COL_WIDTH,
  TEXT_MIN,
  type ColumnSizing,
  type MeasurableColumn,
  type TextMeasurer
} from '../useColumnWidths'

// Deterministic stand-in for canvas measurement: 7px per character.
const perChar: TextMeasurer = (text) => text.length * 7

function sizing(partial: Partial<ColumnSizing>): ColumnSizing {
  return { ideal: 100, min: 100, flexible: false, ...partial }
}

describe('measureColumnIdeals', () => {
  const columns: MeasurableColumn[] = [
    { key: 'name', title: 'Specimen', type: 'text' },
    { key: 'ratio', title: 'Pg/Py', type: 'number' }
  ]

  it('sizes a short numeric column to its header, not the container', () => {
    const rows = [{ name: 'A-1', ratio: 0.2 }]
    const [, ratio] = measureColumnIdeals(columns, rows, perChar)
    const headerMin = 'PG/PY'.length * 7 + HEADER_CHROME + CELL_PAD + LAST_COL_EXTRA
    expect(ratio.ideal).toBe(Math.max(headerMin, IDEAL_FLOOR + LAST_COL_EXTRA))
    // Numeric columns never shrink below their content fit.
    expect(ratio.min).toBe(ratio.ideal)
    expect(ratio.flexible).toBe(false)
  })

  it('sizes a text column to its widest formatted value and keeps it flexible', () => {
    const longest = 'a very long experimental program name'
    const rows = [{ name: 'short' }, { name: longest }]
    const [name] = measureColumnIdeals(columns, rows, perChar)
    expect(name.ideal).toBe(longest.length * 7 + CELL_PAD)
    const headerMin = 'SPECIMEN'.length * 7 + HEADER_CHROME + CELL_PAD
    expect(name.min).toBe(Math.max(headerMin, TEXT_MIN))
    expect(name.flexible).toBe(true)
  })

  it('caps a numeric column even if a value is absurdly wide', () => {
    const rows = [{ name: 'x', ratio: '9'.repeat(200) }]
    const [, ratio] = measureColumnIdeals(columns, rows, perChar)
    expect(ratio.ideal).toBe(CAP_NUMBER + LAST_COL_EXTRA)
  })

  it('uses the format function and skips null/undefined values', () => {
    const withFormat: MeasurableColumn[] = [
      { key: 'ratio', title: 'R', type: 'number', format: (v) => `${v}%` }
    ]
    const rows = [{ ratio: 12345678 }, { ratio: null }, {}]
    const [ratio] = measureColumnIdeals(withFormat, rows, perChar)
    expect(ratio.ideal).toBe('12345678%'.length * 7 + CELL_PAD + LAST_COL_EXTRA)
  })

  it('honours a fixed width override, skipping measurement entirely', () => {
    const fixed: MeasurableColumn[] = [
      { key: 'name', title: 'Specimen', type: 'text', width: 200 },
      { key: 'ratio', title: 'Pg/Py', type: 'number' }
    ]
    const [name] = measureColumnIdeals(fixed, [{ name: 'irrelevant but long text value' }], perChar)
    expect(name).toEqual({ ideal: 200, min: 200, flexible: false })
  })

  it('honours a minWidth override', () => {
    const hinted: MeasurableColumn[] = [
      { key: 'name', title: 'N', type: 'text', minWidth: 300 },
      { key: 'ratio', title: 'R', type: 'number' }
    ]
    const [name] = measureColumnIdeals(hinted, [{ name: 'ab' }], perChar)
    expect(name.min).toBe(300)
    // A floor above the measured ideal raises the ideal with it.
    expect(name.ideal).toBeGreaterThanOrEqual(name.min)
  })
})

describe('distributeWidths', () => {
  it('gives every column its ideal and the leftover to flexible columns when wide', () => {
    const sizings = [
      sizing({ ideal: 200, min: 110, flexible: true }),
      sizing({ ideal: 100, min: 100, flexible: false })
    ]
    const { widths, tableWidth } = distributeWidths(sizings, 1000)
    expect(widths[1]).toBe(100) // the numeric column stays at content fit
    expect(widths[0]).toBe(1000 - SELECT_COL_WIDTH - 100) // text absorbs all leftover
    expect(tableWidth).toBe(1000)
  })

  it('splits leftover across all columns when none are flexible', () => {
    const sizings = [sizing({ ideal: 100, min: 100 }), sizing({ ideal: 300, min: 300 })]
    const { widths } = distributeWidths(sizings, 844)
    // 800 available, 400 ideal → 400 leftover split 1:3
    expect(widths).toEqual([200, 600])
  })

  it('shrinks only flexible columns, proportionally to their slack, when tight', () => {
    const sizings = [
      sizing({ ideal: 300, min: 100, flexible: true }), // slack 200
      sizing({ ideal: 200, min: 100, flexible: true }), // slack 100
      sizing({ ideal: 100, min: 100, flexible: false }) // slack 0
    ]
    // available = 450, sumIdeal = 600 → deficit 150 split 2:1 over the slack
    const { widths, tableWidth } = distributeWidths(sizings, 450 + SELECT_COL_WIDTH)
    expect(widths[0]).toBeCloseTo(200)
    expect(widths[1]).toBeCloseTo(150)
    expect(widths[2]).toBe(100)
    expect(widths.reduce((a, b) => a + b, 0)).toBeCloseTo(450)
    expect(tableWidth).toBe(450 + SELECT_COL_WIDTH)
  })

  it('floors every column at its min and overflows the container when too narrow', () => {
    const sizings = [
      sizing({ ideal: 300, min: 110, flexible: true }),
      sizing({ ideal: 100, min: 100, flexible: false })
    ]
    const { widths, tableWidth } = distributeWidths(sizings, 150)
    expect(widths).toEqual([110, 100])
    // Wider than the 150px container → horizontal scroll engages.
    expect(tableWidth).toBe(110 + 100 + SELECT_COL_WIDTH)
  })

  it('handles an unmeasured (zero-width) container without negative widths', () => {
    const sizings = [sizing({ ideal: 120, min: 90, flexible: true })]
    const { widths, tableWidth } = distributeWidths(sizings, 0)
    expect(widths).toEqual([90])
    expect(tableWidth).toBe(90 + SELECT_COL_WIDTH)
  })

  it('never returns a width below min as the container shrinks (monotone floors)', () => {
    const sizings = [
      sizing({ ideal: 400, min: 110, flexible: true }),
      sizing({ ideal: 90, min: 90, flexible: false })
    ]
    for (let container = 1200; container >= 100; container -= 50) {
      const { widths } = distributeWidths(sizings, container)
      expect(widths[0]).toBeGreaterThanOrEqual(110 - 1e-9)
      expect(widths[1]).toBeGreaterThanOrEqual(90 - 1e-9)
    }
  })
})
