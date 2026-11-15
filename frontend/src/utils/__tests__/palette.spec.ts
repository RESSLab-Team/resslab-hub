import { colorPalette } from '@/utils/palette'
import { describe, expect, it } from 'vitest'

describe('colorPalette', () => {
  it('is the Option 1 palette of #388, in slot order', () => {
    expect(colorPalette).toEqual([
      '#6288BE',
      '#F6C770',
      '#9EDEC2',
      '#D08DB1',
      '#CCCAFD',
      '#EB888C',
      '#AC9EDA',
      '#787496'
    ])
  })

  it('never uses the brand red as a series', () => {
    expect(colorPalette.map((c) => c.toLowerCase())).not.toContain('#e30713')
  })
})
