/**
 * Stable category → color assignment for the dashboard charts.
 *
 * A categorical color has to follow the entity, not its rank: once a reader has
 * learnt "RBS is green", filtering the database must not repaint RBS because it
 * dropped from 3rd to 4th place. So the palette slots are handed out once, from
 * the *unfiltered* dataset, and every chart on a dashboard (treemap, stacked
 * histogram, brush overview) resolves a value through the same scale.
 *
 * Slot order = frequency in the full dataset (most common value first, ties
 * alphabetical): the biggest tiles and series get the most distinguishable
 * leading hues. Values past the 8 palette slots cycle the palette muted toward
 * grey, so the tail still offers a hue hint but reads as secondary.
 */
import { blendHex, colorPalette } from '@/utils/palette'

export type ColorScale = (value: string) => string

/**
 * Pinned palette slots, keyed `'<dataset key>:<field>'` → `{ '<raw value>': slot }`
 * (0-based slot into `colorPalette`; values are the strings as they appear in the
 * data CSV). The frequency rule is stable across filters but a large data upload
 * can reorder the most common values and swap their colors between releases —
 * pin a value here when people have learnt its color, e.g.
 * `'connection:connection_type': { RBS: 2 }`.
 */
export const CATEGORY_COLOR_OVERRIDES: Record<string, Record<string, number>> = {}

/** Color for a value the scale has never seen (dataset not loaded yet). */
export const FALLBACK_CATEGORY_COLOR = '#C1C1C1'

// Grey the tail cycles blend toward; 1st repeat keeps a clear hue hint, later
// repeats are mostly grey.
const TAIL_GREY = '#9E9E9E'
const TAIL_BLEND = [0, 0.55, 0.75]

/** Palette color for a slot index; slots past the palette repeat it muted. */
export function slotColor(slot: number): string {
  const base = colorPalette[slot % colorPalette.length]
  const cycle = Math.floor(slot / colorPalette.length)
  if (cycle === 0) return base
  return blendHex(base, TAIL_GREY, TAIL_BLEND[Math.min(cycle, TAIL_BLEND.length - 1)])
}

/**
 * Distinct values of a categorical field ordered by total count descending,
 * then name ascending. Accepts the backend/aggregate `CountModel` shape (the
 * value is `names[at]`) or the single-chart `{ name, value }` shape.
 */
export type CountLike = { value: number } & ({ names: string[] } | { name: string })

export function categoryDomain(counts: readonly CountLike[], at = 0): string[] {
  const totals = new Map<string, number>()
  for (const count of counts) {
    const name = 'names' in count ? count.names[at] : count.name
    totals.set(name, (totals.get(name) ?? 0) + count.value)
  }
  return [...totals.entries()]
    .sort(([nameA, totalA], [nameB, totalB]) => totalB - totalA || nameA.localeCompare(nameB))
    .map(([name]) => name)
}

/**
 * Build the scale for a domain: overrides claim their slots first, the remaining
 * values fill the remaining slots in domain order. Unknown values get the
 * fallback grey.
 */
export function categoryColorScale(
  domain: readonly string[],
  overrides: Record<string, number> = {}
): ColorScale {
  const taken = new Set<number>()
  const colors = new Map<string, string>()
  for (const value of domain) {
    const slot = overrides[value]
    if (slot !== undefined) {
      taken.add(slot)
      colors.set(value, slotColor(slot))
    }
  }
  let next = 0
  for (const value of domain) {
    if (colors.has(value)) continue
    while (taken.has(next)) next++
    taken.add(next)
    colors.set(value, slotColor(next))
  }
  return (value) => colors.get(value) ?? FALLBACK_CATEGORY_COLOR
}
