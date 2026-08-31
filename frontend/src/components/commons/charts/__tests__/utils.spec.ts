import type { CallbackDataParams } from 'echarts/types/dist/shared'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// measureTextWidth caches into module state, so every test imports a fresh copy.
async function loadUtils() {
  vi.resetModules()
  return import('@/components/commons/charts/utils')
}

let measureText: ReturnType<typeof vi.fn>
let fontListeners: Array<() => void>

beforeEach(() => {
  measureText = vi.fn((text: string) => ({ width: text.length * 10 }))
  vi.spyOn(document, 'createElement').mockImplementation(
    () => ({ getContext: () => ({ font: '', measureText }) } as unknown as HTMLElement)
  )
  fontListeners = []
  Object.defineProperty(document, 'fonts', {
    configurable: true,
    value: {
      addEventListener: (_event: string, handler: () => void) => fontListeners.push(handler)
    }
  })
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('measureTextWidth', () => {
  it('measures once per (text, font) pair', async () => {
    const { measureTextWidth } = await loadUtils()
    const first = measureTextWidth('Connection type', '12px sans-serif')
    const second = measureTextWidth('Connection type', '12px sans-serif')
    expect(second).toBe(first)
    expect(measureText).toHaveBeenCalledTimes(1)
  })

  it('re-measures when the font differs', async () => {
    const { measureTextWidth } = await loadUtils()
    measureTextWidth('Connection type', '12px sans-serif')
    measureTextWidth('Connection type', '18px sans-serif')
    expect(measureText).toHaveBeenCalledTimes(2)
  })

  it('measures distinct strings separately', async () => {
    const { measureTextWidth } = await loadUtils()
    expect(measureTextWidth('ab', '12px sans-serif')).toBe(20)
    expect(measureTextWidth('abcd', '12px sans-serif')).toBe(40)
  })

  // A width measured against the fallback face would otherwise stick forever.
  it('drops cached widths once the webfont finishes loading', async () => {
    const { measureTextWidth } = await loadUtils()
    measureTextWidth('Connection type', '12px sans-serif')
    expect(fontListeners).toHaveLength(1)
    fontListeners.forEach((notify) => notify())
    measureTextWidth('Connection type', '12px sans-serif')
    expect(measureText).toHaveBeenCalledTimes(2)
  })
})

describe('buildFigureTooltipFormatter', () => {
  const params = (name: string, value: number) =>
    ({ name, value, data: { originalName: name } } as unknown as CallbackDataParams)

  it('appends the figure of the hovered category', async () => {
    const { buildFigureTooltipFormatter } = await loadUtils()
    const format = buildFigureTooltipFormatter(
      (value) => (value === 'CNT' ? '/img/cnt.png' : undefined),
      (p) => (p.data as { originalName: string }).originalName
    )
    const html = format(params('CNT', 65))
    expect(html).toContain('CNT')
    expect(html).toContain('65')
    expect(html).toContain('<img src="/img/cnt.png"')
  })

  it('falls back to name and count when the category has no figure', async () => {
    const { buildFigureTooltipFormatter } = await loadUtils()
    const format = buildFigureTooltipFormatter(
      () => undefined,
      (p) => p.name
    )
    const html = format(params('DEMO-SPEC-01', 15))
    expect(html).toContain('DEMO-SPEC-01')
    expect(html).not.toContain('<img')
  })

  // Category names come from the database and land in raw tooltip HTML.
  it('escapes the category name', async () => {
    const { buildFigureTooltipFormatter } = await loadUtils()
    const format = buildFigureTooltipFormatter(
      () => undefined,
      (p) => p.name
    )
    expect(format(params('<script>x</script>', 1))).not.toContain('<script>')
  })

  // trigger: 'item' hands over one item, but the callback type allows the axis form.
  it('reads the first item when given the axis form', async () => {
    const { buildFigureTooltipFormatter } = await loadUtils()
    const format = buildFigureTooltipFormatter(
      () => '/img/gp.png',
      (p) => p.name
    )
    expect(format([params('GP', 37)])).toContain('<img src="/img/gp.png"')
  })
})

describe('buildFigureTooltipPosition', () => {
  // A dashboard chart cell: 480x100, sitting `top` px down the window.
  const chartRect = (top: number) =>
    ({ left: 40, top, right: 520, bottom: top + 100, width: 480, height: 100 } as DOMRect)
  const size = {
    contentSize: [240, 300] as [number, number],
    viewSize: [480, 100] as [number, number]
  }
  // Results come back in chart space; page space is what the window clamps to.
  const toPage = (xy: [number, number], top: number) => [40 + xy[0], top + xy[1]]

  beforeEach(() => {
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 900 })
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: 800 })
  })

  it('sits just off the cursor, not across the window', async () => {
    const { buildFigureTooltipPosition } = await loadUtils()
    const place = buildFigureTooltipPosition(() => chartRect(300))
    const [x, y] = toPage(place([100, 50], null, null, null, size), 300)
    expect(x).toBe(40 + 100 + 16) // offset to the right of the pointer
    expect(y).toBe(300 + 50 - 150) // centred on it vertically
  })

  it('flips to the left of the cursor when the right would overflow', async () => {
    const { buildFigureTooltipPosition } = await loadUtils()
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 700 })
    const place = buildFigureTooltipPosition(() => chartRect(300))
    // Pointer at page x 500: 500 + 16 + 240 runs past the 700px window.
    const [x] = toPage(place([460, 50], null, null, null, size), 300)
    expect(x + 240).toBeLessThanOrEqual(500) // entirely left of the pointer
  })

  it('shifts back into the window instead of running off the bottom', async () => {
    const { buildFigureTooltipPosition } = await loadUtils()
    const place = buildFigureTooltipPosition(() => chartRect(700))
    const [, y] = toPage(place([100, 50], null, null, null, size), 700)
    expect(y + 300).toBeLessThanOrEqual(800)
    expect(y).toBeGreaterThanOrEqual(0)
  })

  it('falls back to the cursor when the chart is not measurable yet', async () => {
    const { buildFigureTooltipPosition } = await loadUtils()
    const place = buildFigureTooltipPosition(() => undefined)
    expect(place([12, 34], null, null, null, size)).toEqual([12, 34])
  })
})
