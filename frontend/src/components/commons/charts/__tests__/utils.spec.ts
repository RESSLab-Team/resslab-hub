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
