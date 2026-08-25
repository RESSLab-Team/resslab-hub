import {
  categoryColorScale,
  categoryDomain,
  FALLBACK_CATEGORY_COLOR,
  slotColor
} from '@/utils/categoryColors'
import { colorPalette } from '@/utils/palette'
import { describe, expect, it } from 'vitest'

const full = [
  { names: ['WUF-B'], value: 31 },
  { names: ['WUF-W'], value: 24 },
  { names: ['RBS'], value: 20 },
  { names: ['BFP'], value: 11 },
  { names: ['KBB'], value: 7 },
  { names: ['WFP'], value: 4 },
  { names: ['BEEP'], value: 3 }
]

describe('categoryDomain', () => {
  it('orders by total descending, then name ascending', () => {
    const counts = [
      { names: ['b'], value: 2 },
      { names: ['a'], value: 2 },
      { names: ['c'], value: 5 }
    ]
    expect(categoryDomain(counts)).toEqual(['c', 'a', 'b'])
  })

  it('sums across the other field and reads the requested position', () => {
    const counts = [
      { names: ['2001', 'RBS'], value: 1 },
      { names: ['2002', 'RBS'], value: 4 },
      { names: ['2001', 'BFP'], value: 3 }
    ]
    expect(categoryDomain(counts, 1)).toEqual(['RBS', 'BFP'])
  })

  it('accepts the single-chart { name, value } shape', () => {
    expect(
      categoryDomain([
        { name: 'x', value: 1 },
        { name: 'y', value: 3 }
      ])
    ).toEqual(['y', 'x'])
  })
})

describe('categoryColorScale', () => {
  it('assigns palette slots in domain order', () => {
    const scale = categoryColorScale(categoryDomain(full))
    expect(scale('WUF-B')).toBe(colorPalette[0])
    expect(scale('WUF-W')).toBe(colorPalette[1])
    expect(scale('RBS')).toBe(colorPalette[2])
    expect(scale('BEEP')).toBe(colorPalette[6])
  })

  it('keeps a value on its color whatever subset is shown', () => {
    const scale = categoryColorScale(categoryDomain(full))
    // RBS drops from 3rd to 4th place in this selection; its color is the scale's, not its rank's
    const filtered = [
      { names: ['BFP'], value: 9 },
      { names: ['WUF-B'], value: 5 },
      { names: ['KBB'], value: 4 },
      { names: ['RBS'], value: 2 }
    ]
    for (const count of filtered) {
      expect(scale(count.names[0])).toBe(categoryColorScale(categoryDomain(full))(count.names[0]))
    }
    expect(scale('RBS')).toBe(colorPalette[2])
  })

  it('lets overrides pin a slot and fills the others around it', () => {
    const scale = categoryColorScale(categoryDomain(full), { RBS: 0 })
    expect(scale('RBS')).toBe(colorPalette[0])
    expect(scale('WUF-B')).toBe(colorPalette[1])
    expect(scale('WUF-W')).toBe(colorPalette[2])
    expect(scale('BFP')).toBe(colorPalette[3])
  })

  it('mutes the palette for values past the last slot instead of repeating it', () => {
    const domain = Array.from({ length: 2 * colorPalette.length + 1 }, (_, i) => `v${i}`)
    const scale = categoryColorScale(domain)
    const n = colorPalette.length
    expect(scale('v0')).toBe(colorPalette[0])
    expect(scale(`v${n}`)).not.toBe(colorPalette[0])
    expect(scale(`v${n}`)).toBe(slotColor(n))
    expect(scale(`v${2 * n}`)).not.toBe(scale(`v${n}`))
    // hue hint survives: the muted blue is still bluer than it is red
    const hex = scale(`v${n}`)
    const red = parseInt(hex.slice(1, 3), 16)
    const blue = parseInt(hex.slice(5, 7), 16)
    expect(blue).toBeGreaterThan(red)
  })

  it('returns the fallback grey for unknown values', () => {
    expect(categoryColorScale(['a'])('zzz')).toBe(FALLBACK_CATEGORY_COLOR)
  })
})
