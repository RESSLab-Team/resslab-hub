import { MapCategory } from '@/backend'
import {
  MAP_CATEGORIES,
  categoryFor,
  categoryIndex,
  colorFor,
  routeFor
} from '@/utils/mapCategories'
import { DATABASES } from '@/utils/navigation'
import { describe, expect, it } from 'vitest'

describe('mapCategories', () => {
  it('has every backend category once', () => {
    expect(MAP_CATEGORIES.map((entry) => entry.id).sort()).toEqual(
      Object.values(MapCategory).sort()
    )
  })

  it('gives each category its own colour', () => {
    const colors = MAP_CATEGORIES.map((entry) => entry.color.toLowerCase())
    expect(new Set(colors).size).toBe(colors.length)
    for (const color of colors) expect(color).toMatch(/^#[0-9a-f]{6}$/)
  })

  it('links each category to an existing database page', () => {
    const pages = new Set(DATABASES.map((database) => database.to))
    for (const entry of MAP_CATEGORIES) expect(pages).toContain(entry.to)
  })

  it('looks a category up by id', () => {
    expect(categoryIndex(MapCategory.Braces)).toBe(0)
    expect(categoryIndex(MapCategory.EccentricBracedFrame)).toBe(8)
    expect(routeFor(MapCategory.TensileCoupon)).toBe('/materials/tensile-coupons')
    expect(colorFor(MapCategory.Braces)).toBe(MAP_CATEGORIES[0].color)
    expect(categoryIndex('nope' as MapCategory)).toBe(-1)
    expect(() => categoryFor('nope' as MapCategory)).toThrow('unknown map category')
  })
})
