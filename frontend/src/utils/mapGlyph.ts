/**
 * The map marker: a square whose area follows the test count, split as a
 * small treemap by category, with the count on an ink tab (the design's
 * "treemap" glyph). The design draws it as an SVG string; here it is built
 * from DOM nodes with textContent only, so a site name is never parsed as
 * HTML. The look (borders, tab, outline) is CSS in OverviewMap.vue.
 */
import type { MapCategory } from '@/backend'
import { categoryIndex, colorFor } from '@/utils/mapCategories'
import type { Counts } from '@/utils/mapSites'

/** height of the count tab above the square, in px */
export const TAB_HEIGHT = 16
/** glyph scale of the compact variant */
export const COMPACT_SCALE = 0.74

/**
 * Side of the square in px. The area follows n, relative to `nref`; a
 * cluster bigger than `nref` grows up to sqrt(1.4) times more, not further.
 */
export function glyphSize(n: number, nref: number, k = 1): number {
  const ratio = nref > 0 ? Math.min(Math.max(n, 0) / nref, 1.4) : 0
  return Math.round((22 + 54 * Math.sqrt(ratio)) * k)
}

/** The count on the tab: 950, 1.2k, 12k. */
export function shortCount(n: number): string {
  if (n >= 10000) return `${Math.round(n / 1000)}k`
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
  return String(n)
}

export function truncate(text: string, max: number): string {
  return text.length > max ? text.slice(0, max - 1).trim() + '…' : text
}

export interface Cell {
  id: MapCategory
  n: number
  x: number
  y: number
  w: number
  h: number
}

interface Item {
  id: MapCategory
  n: number
}

const sumOf = (items: Item[]) => items.reduce((a, item) => a + item.n, 0)

function split(items: Item[], x: number, y: number, w: number, h: number): Cell[] {
  if (items.length === 1) return [{ ...items[0], x, y, w, h }]
  const total = sumOf(items)
  // Cut where the running sum reaches half, along the longer side.
  let acc = 0
  let idx = 1
  for (let i = 0; i < items.length; i++) {
    acc += items[i].n
    if (acc >= total / 2) {
      idx = i + 1
      break
    }
  }
  idx = Math.max(1, Math.min(items.length - 1, idx))
  const first = items.slice(0, idx)
  const rest = items.slice(idx)
  const share = sumOf(first) / total
  if (w >= h) {
    const w1 = w * share
    return [...split(first, x, y, w1, h), ...split(rest, x + w1, y, w - w1, h)]
  }
  const h1 = h * share
  return [...split(first, x, y, w, h1), ...split(rest, x, y + h1, w, h - h1)]
}

/** A binary treemap of the counts in the rectangle, biggest first. */
export function treemap(counts: Counts, x: number, y: number, w: number, h: number): Cell[] {
  const items = (Object.entries(counts) as [MapCategory, number][])
    .filter(([, n]) => n > 0)
    .map(([id, n]) => ({ id, n }))
    .sort((a, b) => b.n - a.n || categoryIndex(a.id) - categoryIndex(b.id))
  return items.length > 0 ? split(items, x, y, w, h) : []
}

function node(tag: string, className: string, text?: string): HTMLElement {
  const el = document.createElement(tag)
  el.className = className
  if (text !== undefined) el.textContent = text
  return el
}

export interface GlyphOptions {
  counts: Counts
  n: number
  /** side of the square, from glyphSize() */
  size: number
  cluster?: boolean
  /** shown next to the tab when the map is zoomed in enough (CSS decides) */
  name?: string | null
  /** for screen readers */
  label?: string
}

/**
 * The marker element. Its own box is the square, so a maplibre Marker with
 * anchor "center" puts the square's centre on the point; the tab, the name
 * and the cluster shadow overflow it.
 *
 *   div.mg                 the square's box, the marker element
 *     div.mg-wrap          tab row + square, as wide as the wider of the two
 *       div.mg-shadow      clusters only: a second square offset by 4px
 *       div.mg-head        span.mg-tab (count) + span.mg-name
 *       div.mg-box         div.mg-cell per category
 *       div.mg-sel         selection outline around the wrap
 */
export function glyphElement(options: GlyphOptions): HTMLElement {
  const { counts, n, size, cluster = false, name, label } = options
  const root = node('div', cluster ? 'mg mg-cluster' : 'mg')
  root.style.width = `${size}px`
  root.style.height = `${size}px`
  // Small squares above big ones, so a small site next to a big one stays clickable.
  root.style.zIndex = String(500 - size)
  root.setAttribute('role', 'button')
  root.tabIndex = 0
  if (label) root.setAttribute('aria-label', label)

  const wrap = node('div', 'mg-wrap')
  wrap.style.minWidth = `${size}px`
  wrap.style.top = `${-TAB_HEIGHT}px`

  if (cluster) {
    const shadow = node('div', 'mg-shadow')
    shadow.style.width = `${size}px`
    shadow.style.height = `${size}px`
    shadow.style.top = `${TAB_HEIGHT + 4}px`
    wrap.append(shadow)
  }

  const head = node('div', 'mg-head')
  head.append(node('span', 'mg-tab', shortCount(n)))
  if (name) head.append(node('span', 'mg-name', name))

  const box = node('div', 'mg-box')
  box.style.width = `${size}px`
  box.style.height = `${size}px`
  // Cells sit inside the 1px border with a 1px gap between them: lay out on
  // (size - 1) and draw each cell 1px smaller, as the design does.
  for (const cell of treemap(counts, 0, 0, size - 1, size - 1)) {
    const el = node('div', 'mg-cell')
    el.style.left = `${cell.x}px`
    el.style.top = `${cell.y}px`
    el.style.width = `${Math.max(0.5, cell.w - 1)}px`
    el.style.height = `${Math.max(0.5, cell.h - 1)}px`
    el.style.background = colorFor(cell.id)
    box.append(el)
  }

  wrap.append(head, box, node('div', 'mg-sel'))
  root.append(wrap)
  return root
}

/** Selected: solid red outline and red tab. Highlighted (hover in the panel): dashed outline. */
export function setGlyphState(
  el: HTMLElement,
  state: { selected?: boolean; highlighted?: boolean }
): void {
  if (state.selected !== undefined) el.classList.toggle('is-sel', state.selected)
  if (state.highlighted !== undefined) el.classList.toggle('is-hl', state.highlighted)
}
