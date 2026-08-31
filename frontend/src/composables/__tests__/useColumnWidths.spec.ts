import { describe, expect, it } from 'vitest'
import { effectScope, ref } from 'vue'
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
  useColumnWidths,
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

  it('measures strong (bold identifier) cells with the strong font role', () => {
    const fonts: string[] = []
    const spy: TextMeasurer = (text, font) => {
      fonts.push(font)
      return text.length * 7
    }
    const strong: MeasurableColumn[] = [
      { key: 'name', title: 'Specimen', type: 'text', cellVariant: 'strong' }
    ]
    measureColumnIdeals(strong, [{ name: 'CNT_L1_M_C1_R1_0' }], spy)
    expect(fonts).toEqual(['header', 'strong'])
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

const LONG_TITLE = 'Total Doubler Plate Thickness [mm]'
const SHORT_TITLE = 'tdp,tot [mm]'

// Case-sensitive spy around the per-char fake, capturing header measurements.
function recordingMeasurer(): { measure: TextMeasurer; seenHeaders: string[] } {
  const seenHeaders: string[] = []
  const measure: TextMeasurer = (text, font) => {
    if (font === 'header') seenHeaders.push(text)
    return text.length * 7
  }
  return { measure, seenHeaders }
}

describe('measureColumnIdeals (short titles)', () => {
  const shortable: MeasurableColumn[] = [
    {
      key: 't_dp_tot',
      title: LONG_TITLE,
      type: 'number',
      shortTitle: { text: SHORT_TITLE, isSymbol: false }
    }
  ]

  it('uses the short title for the header floor in short mode', () => {
    const [short] = measureColumnIdeals(shortable, [], perChar, true)
    const headerMin = SHORT_TITLE.length * 7 + HEADER_CHROME + CELL_PAD
    expect(short.ideal).toBe(Math.max(headerMin, IDEAL_FLOOR) + LAST_COL_EXTRA)
    const [long] = measureColumnIdeals(shortable, [], perChar)
    expect(short.ideal).toBeLessThan(long.ideal)
  })

  it('measures a symbol short title verbatim — no uppercasing', () => {
    const symbolColumn: MeasurableColumn[] = [
      {
        key: 't_dp_tot',
        title: LONG_TITLE,
        type: 'number',
        shortTitle: { text: SHORT_TITLE, isSymbol: true }
      }
    ]
    const { measure, seenHeaders } = recordingMeasurer()
    measureColumnIdeals(symbolColumn, [], measure, true)
    expect(seenHeaders).toContain(SHORT_TITLE)
    expect(seenHeaders).not.toContain(SHORT_TITLE.toUpperCase())
  })

  it('measures a word short title uppercased, like any header', () => {
    const { measure, seenHeaders } = recordingMeasurer()
    measureColumnIdeals(shortable, [], measure, true)
    expect(seenHeaders).toContain(SHORT_TITLE.toUpperCase())
    expect(seenHeaders).not.toContain(SHORT_TITLE)
  })

  it('keeps the (uppercased) long title for columns without a short title in short mode', () => {
    const mixed: MeasurableColumn[] = [
      { key: 'name', title: 'Specimen', type: 'text' },
      ...shortable
    ]
    const { measure, seenHeaders } = recordingMeasurer()
    measureColumnIdeals(mixed, [], measure, true)
    expect(seenHeaders).toContain('SPECIMEN')
  })

  it('ignores shortTitle entirely in long mode', () => {
    const [withShort] = measureColumnIdeals(shortable, [], perChar)
    const [withoutShort] = measureColumnIdeals(
      [{ key: 't_dp_tot', title: LONG_TITLE, type: 'number' }],
      [],
      perChar
    )
    expect(withShort).toEqual(withoutShort)
  })
})

describe('useColumnWidths (adaptive switch)', () => {
  const px = (value: string): number => parseFloat(value)

  function adaptiveColumns(withShort: boolean): MeasurableColumn[] {
    return [
      { key: 'name', title: 'Experimental Program', type: 'text' },
      {
        key: 't_dp_tot',
        title: LONG_TITLE,
        type: 'number',
        shortTitle: withShort ? { text: SHORT_TITLE, isSymbol: true } : undefined
      }
    ]
  }

  function setup(cols: MeasurableColumn[], container: number) {
    const scope = effectScope()
    const columns = ref(cols)
    const rows = ref<readonly Record<string, unknown>[]>([{ name: 'A-1', t_dp_tot: 20 }])
    const containerWidth = ref(container)
    const api = scope.run(() => useColumnWidths(columns, rows, containerWidth))!
    return { ...api, columns }
  }

  it('prefers long titles when they fit the container', () => {
    const { useShortTitles } = setup(adaptiveColumns(true), 2000)
    expect(useShortTitles.value).toBe(false)
  })

  it('switches to short labels when the long mins overflow, and the table shrinks', () => {
    const narrow = 300
    const long = setup(adaptiveColumns(false), narrow)
    const short = setup(adaptiveColumns(true), narrow)
    expect(short.useShortTitles.value).toBe(true)
    expect(px(short.tableWidth.value)).toBeLessThan(px(long.tableWidth.value))
  })

  it('stays long when no column is shortable, however narrow the container', () => {
    const { useShortTitles } = setup(adaptiveColumns(false), 50)
    expect(useShortTitles.value).toBe(false)
  })

  it('shrinks ratcheted widths when short titles arrive asynchronously', () => {
    const { columns, tableWidth, useShortTitles } = setup(adaptiveColumns(false), 300)
    const before = px(tableWidth.value)
    expect(useShortTitles.value).toBe(false)
    // The dictionary fetch lands: same column keys, now carrying short labels.
    columns.value = adaptiveColumns(true)
    expect(useShortTitles.value).toBe(true)
    expect(px(tableWidth.value)).toBeLessThan(before)
  })
})
