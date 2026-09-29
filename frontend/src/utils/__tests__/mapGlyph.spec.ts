import {
  glyphElement,
  glyphSize,
  setGlyphState,
  shortCount,
  treemap,
  truncate
} from '@/utils/mapGlyph'
import { colorFor } from '@/utils/mapCategories'
import { MapCategory } from '@/backend'
import { describe, expect, it } from 'vitest'

describe('mapGlyph.glyphSize', () => {
  it('goes from 22px to 76px at the reference count', () => {
    expect(glyphSize(0, 300)).toBe(22)
    expect(glyphSize(300, 300)).toBe(76)
  })

  it('grows with n and stops at 1.4 times the reference', () => {
    const sizes = [1, 10, 50, 150, 300].map((n) => glyphSize(n, 300))
    expect([...sizes].sort((a, b) => a - b)).toEqual(sizes)
    expect(glyphSize(420, 300)).toBe(glyphSize(10000, 300))
    expect(glyphSize(420, 300)).toBe(Math.round(22 + 54 * Math.sqrt(1.4)))
  })

  it('scales for the compact variant and survives an empty dataset', () => {
    expect(glyphSize(300, 300, 0.5)).toBe(38)
    expect(glyphSize(5, 0)).toBe(22)
  })
})

describe('mapGlyph.shortCount', () => {
  it('shortens thousands', () => {
    expect(shortCount(950)).toBe('950')
    expect(shortCount(1234)).toBe('1.2k')
    expect(shortCount(12345)).toBe('12k')
  })

  it('truncates long names with an ellipsis', () => {
    expect(truncate('EPFL', 16)).toBe('EPFL')
    expect(truncate('University of Naples Federico II', 16)).toBe('University of N…')
  })
})

describe('mapGlyph.treemap', () => {
  const counts = { braces: 10, columns: 30, materials: 60, 'hss-column': 0 }

  it('covers the square, one cell per non-zero category, biggest first', () => {
    const cells = treemap(counts, 0, 0, 40, 40)
    expect(cells.map((cell) => cell.id)).toEqual(['materials', 'columns', 'braces'])
    const area = cells.reduce((sum, cell) => sum + cell.w * cell.h, 0)
    expect(area).toBeCloseTo(1600)
  })

  it('gives each cell an area proportional to its count, inside the square', () => {
    for (const cell of treemap(counts, 5, 5, 40, 40)) {
      expect(cell.w * cell.h).toBeCloseTo((1600 * cell.n) / 100)
      expect(cell.x).toBeGreaterThanOrEqual(5)
      expect(cell.y).toBeGreaterThanOrEqual(5)
      expect(cell.x + cell.w).toBeLessThanOrEqual(45 + 1e-9)
      expect(cell.y + cell.h).toBeLessThanOrEqual(45 + 1e-9)
    }
  })

  it('fills the square with a single category and returns nothing when empty', () => {
    expect(treemap({ braces: 7 }, 0, 0, 30, 30)).toEqual([
      { id: 'braces', n: 7, x: 0, y: 0, w: 30, h: 30 }
    ])
    expect(treemap({}, 0, 0, 30, 30)).toEqual([])
  })
})

describe('mapGlyph.glyphElement', () => {
  it('builds the square, its cells and the count tab', () => {
    const el = glyphElement({
      counts: { braces: 1200, columns: 300 },
      n: 1500,
      size: 60,
      label: 'EPFL, 1500 tests'
    })
    expect(el.classList.contains('mg')).toBe(true)
    expect(el.style.width).toBe('60px')
    expect(el.style.zIndex).toBe('440')
    expect(el.getAttribute('role')).toBe('button')
    expect(el.getAttribute('aria-label')).toBe('EPFL, 1500 tests')
    expect(el.querySelector('.mg-tab')?.textContent).toBe('1.5k')
    expect(el.querySelector('.mg-name')).toBeNull()
    expect(el.querySelector('.mg-shadow')).toBeNull()
    const cells = el.querySelectorAll<HTMLElement>('.mg-cell')
    expect(cells).toHaveLength(2)
    const probe = document.createElement('div')
    probe.style.background = colorFor(MapCategory.Braces)
    expect(cells[0].style.background).toBe(probe.style.background)
  })

  it('adds the name as text and a shadow for clusters', () => {
    const el = glyphElement({
      counts: { braces: 3 },
      n: 3,
      size: 30,
      cluster: true,
      name: '<b>3 sites</b>'
    })
    expect(el.classList.contains('mg-cluster')).toBe(true)
    expect(el.querySelector('.mg-shadow')).not.toBeNull()
    expect(el.querySelector('.mg-name')?.textContent).toBe('<b>3 sites</b>')
    expect(el.querySelector('b')).toBeNull()
  })

  it('toggles the selected and highlighted states', () => {
    const el = glyphElement({ counts: { braces: 1 }, n: 1, size: 22 })
    setGlyphState(el, { selected: true })
    expect(el.classList.contains('is-sel')).toBe(true)
    setGlyphState(el, { highlighted: true })
    expect(el.classList.contains('is-sel')).toBe(true)
    expect(el.classList.contains('is-hl')).toBe(true)
    setGlyphState(el, { selected: false, highlighted: false })
    expect(el.className).toBe('mg')
  })
})
