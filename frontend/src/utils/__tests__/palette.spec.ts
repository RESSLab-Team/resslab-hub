import { colorPalette } from '@/utils/palette'
import hexRgb from 'hex-rgb'
import { describe, expect, it } from 'vitest'

/** WCAG 2 relative luminance of a hex colour. */
function luminance(hex: string): number {
  const { red, green, blue } = hexRgb(hex)
  const [r, g, b] = [red, green, blue].map((c) => {
    const s = c / 255
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

/** WCAG 2 contrast ratio between two hex colours. */
function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x)
  return (hi + 0.05) / (lo + 0.05)
}

describe('colorPalette', () => {
  it('is the Option F palette of #388, in slot order', () => {
    expect(colorPalette).toEqual([
      '#0072C3',
      '#00539A',
      '#9F1853',
      '#726E6E',
      '#D02670',
      '#005D5D',
      '#8A3FFC',
      '#6929C4'
    ])
  })

  it('never uses the brand red as a series', () => {
    expect(colorPalette.map((c) => c.toLowerCase())).not.toContain('#e30713')
  })

  // The treemap labels are white on every tile (SingleChart.vue).
  it('keeps white text readable on every slot (4.5:1 or more)', () => {
    for (const color of colorPalette) {
      expect(contrast(color, '#FFFFFF'), color).toBeGreaterThanOrEqual(4.5)
    }
  })
})
