/**
 * Content-measured column widths for the light-DOM table.
 *
 * The table is `table-layout: fixed`, so column widths come entirely from the
 * `<colgroup>` — nothing is ever sized from cell content by the browser. This
 * composable measures the real content instead: every column's header and the
 * formatted values of the committed page are measured off-screen (canvas
 * `measureText`), giving each column an `ideal` width (content-fit) and a `min`
 * width (what it keeps when space is tight). A pure distribution step then maps
 * those onto the container:
 *
 *   1. container ≥ Σideal  — every column gets its ideal; the leftover goes to
 *      the text/option columns (they hold prose worth the room), so a numeric
 *      column like "Pg/Py" stays at header width instead of trapping space.
 *   2. Σmin ≤ container < Σideal — numeric columns keep their ideal; text
 *      columns shrink proportionally to their slack until everything fits.
 *   3. container < Σmin — every column gets its min and the table becomes wider
 *      than the container, engaging the horizontal scroll wrapper.
 *
 * Measured widths are RATCHETED per column key: they only ever grow within a
 * component's lifetime, so filtering/paging to a subset never makes columns
 * jitter narrower mid-interaction. The ratchet resets only when the column set
 * changes or when the web font finishes loading (fallback-font metrics are
 * replaced wholesale).
 *
 * The measurement and distribution helpers are pure (measurer injected) so they
 * can be unit tested without a DOM, mirroring `useVirtualRows.ts`.
 */
import { computed, onScopeDispose, ref, type ComputedRef, type Ref } from 'vue'
import type { ColumnType } from './table'

/** Fixed width of the leading select-checkbox column (see `.stbl-col-select`). */
export const SELECT_COL_WIDTH = 44
/** Horizontal cell padding: 16px each side (see `.stbl-table tbody td`). */
export const CELL_PAD = 32
/** Non-text chrome inside a header cell: caret 12 + sort icon 14 + flex gaps.
 *  Always reserved, so sorting a column never changes its width. */
export const HEADER_CHROME = 30
/** Extra right padding on the last column clearing the overlay scrollbar
 *  (`--stbl-sbar-inset + --stbl-sbar-w + 12px` minus the normal 16px). */
export const LAST_COL_EXTRA = 7
/** No column may be narrower than this, whatever it contains. */
export const IDEAL_FLOOR = 72
/** Tight-space floor for text/option columns (numbers floor at their ideal). */
export const TEXT_MIN = 110
/** Content-fit caps — one absurdly long value must not balloon a column. */
export const CAP_TEXT = 480
export const CAP_NUMBER = 260
/** `tag` pill chrome: 8px padding each side (the table drops the global border). */
const TAG_EXTRA = 16
/** Canvas can't apply `tnum`/`<sub>` metrics — pad every measurement a little. */
const SAFETY_RATIO = 1.03
const SAFETY_PX = 2

/** Font roles mirroring the table CSS (sizes from SimpleTable's scoped styles). */
export type MeasureFont = 'body' | 'mono' | 'tag' | 'strong' | 'header'

export type TextMeasurer = (text: string, font: MeasureFont) => number

export interface MeasurableColumn {
  key: string
  /** Plain-text header (the `<sub>` markup already stripped). */
  title: string
  /** Plain-text adaptive short label. `isSymbol` marks an engineering symbol
   *  whose case is semantic (t ≠ T) — rendered and measured verbatim instead
   *  of uppercased. */
  shortTitle?: { text: string; isSymbol: boolean }
  type: ColumnType
  format?: (value: unknown) => string
  cellVariant?: 'mono' | 'tag' | 'strong'
  categoryColor?: boolean
  /** Fixed width in px — skips measurement; the column never grows or shrinks. */
  width?: number
  /** Tight-space floor in px, overriding the type default. */
  minWidth?: number
}

export interface ColumnSizing {
  ideal: number
  min: number
  /** Text/option columns without a fixed width absorb leftover space. */
  flexible: boolean
}

/* ---- Canvas text measurement ---------------------------------------------- */

const measureCache = new Map<string, number>()
let canvasCtx: CanvasRenderingContext2D | null | undefined
let fontFamily: string | undefined
let fontsSettled = false

// One shared font-swap hook: when the web font lands, cached fallback-font
// widths are wrong wholesale — drop them once, then notify every live table.
const fontSwapListeners = new Set<() => void>()
if (typeof document !== 'undefined' && 'fonts' in document) {
  document.fonts.ready.then(() => {
    fontsSettled = true
    measureCache.clear()
    fontSwapListeners.forEach((listener) => listener())
  })
}

function contextFont(font: MeasureFont): string {
  if (fontFamily === undefined) {
    fontFamily = getComputedStyle(document.body).fontFamily || 'sans-serif'
  }
  switch (font) {
    case 'header':
      return `700 11px ${fontFamily}`
    case 'mono':
      return `12px ${fontFamily}`
    case 'tag':
      return `600 11px ${fontFamily}`
    case 'strong':
      return `600 13px ${fontFamily}`
    default:
      return `13px ${fontFamily}`
  }
}

/**
 * Measure rendered text width in px for one of the table's font roles.
 * Falls back to a per-character estimate where canvas is unavailable (jsdom).
 */
export function measureTableText(text: string, font: MeasureFont): number {
  const key = `${font}|${text}`
  const cached = measureCache.get(key)
  if (cached !== undefined) return cached
  if (canvasCtx === undefined) {
    canvasCtx = document.createElement('canvas').getContext('2d')
  }
  let width: number
  if (canvasCtx) {
    canvasCtx.font = contextFont(font)
    width = canvasCtx.measureText(text).width
    // Headers letter-space at 0.06em (0.66px at 11px) — canvas has no
    // letter-spacing outside Chromium, so add it per character.
    if (font === 'header') width += text.length * 0.66
  } else {
    width = text.length * (font === 'body' || font === 'strong' ? 7.5 : 7)
  }
  width = width * SAFETY_RATIO + SAFETY_PX
  measureCache.set(key, width)
  return width
}

/* ---- Pure sizing helpers --------------------------------------------------- */

/**
 * Compute each column's content-fit `ideal` and tight-space `min` from its
 * header and the formatted values of the given rows.
 */
export function measureColumnIdeals(
  columns: MeasurableColumn[],
  rows: readonly Record<string, unknown>[],
  measure: TextMeasurer,
  useShortTitles = false
): ColumnSizing[] {
  return columns.map((column, index) => {
    const lastExtra = index === columns.length - 1 ? LAST_COL_EXTRA : 0
    if (column.width !== undefined) {
      const fixed = column.width + lastExtra
      return { ideal: fixed, min: fixed, flexible: false }
    }
    const isText = column.type === 'text' || column.type === 'option'
    // Headers render uppercased (CSS text-transform) — measure what shows.
    // Short symbol labels are the exception: their case is semantic (t ≠ T),
    // so they render and measure verbatim.
    const short = useShortTitles ? column.shortTitle : undefined
    const headerText = short
      ? short.isSymbol
        ? short.text
        : short.text.toUpperCase()
      : column.title.toUpperCase()
    const headerMin = measure(headerText, 'header') + HEADER_CHROME + CELL_PAD
    // Category-colored cells render as tag pills whatever their variant.
    const isTag = column.cellVariant === 'tag' || column.categoryColor === true
    const cellFont: MeasureFont =
      column.cellVariant === 'mono'
        ? 'mono'
        : isTag
        ? 'tag'
        : column.cellVariant === 'strong'
        ? 'strong'
        : 'body'
    const tagExtra = isTag ? TAG_EXTRA : 0
    let contentW = 0
    for (const row of rows) {
      const value = row[column.key]
      if (value === null || value === undefined) continue
      const text = column.format ? column.format(value) : String(value)
      if (!text) continue
      const width = measure(text, cellFont) + tagExtra + CELL_PAD
      if (width > contentW) contentW = width
    }
    const cap = (isText ? CAP_TEXT : CAP_NUMBER) + lastExtra
    const ideal = Math.min(Math.max(headerMin, contentW, IDEAL_FLOOR) + lastExtra, cap)
    let min: number
    if (column.minWidth !== undefined) {
      min = column.minWidth + lastExtra
    } else if (isText) {
      min = Math.min(Math.max(headerMin, TEXT_MIN) + lastExtra, ideal)
    } else {
      // Numeric/boolean columns are already small — they never shrink below
      // content fit, which is what keeps them readable when space runs out.
      min = ideal
    }
    return { ideal: Math.max(ideal, min), min, flexible: isText }
  })
}

/**
 * Map per-column ideal/min sizes onto a container width. Returns px widths for
 * the data columns and the total table width (container-fit, or wider when the
 * mins don't fit — that overflow is what the horizontal scroll wrapper shows).
 */
export function distributeWidths(
  sizings: ColumnSizing[],
  containerWidth: number,
  selectColWidth = SELECT_COL_WIDTH
): { widths: number[]; tableWidth: number } {
  if (sizings.length === 0) {
    return { widths: [], tableWidth: Math.max(containerWidth, selectColWidth) }
  }
  const available = containerWidth - selectColWidth
  const sumIdeal = sizings.reduce((sum, s) => sum + s.ideal, 0)
  const sumMin = sizings.reduce((sum, s) => sum + s.min, 0)
  if (available >= sumIdeal) {
    const leftover = available - sumIdeal
    const flexTotal = sizings.reduce((sum, s) => (s.flexible ? sum + s.ideal : sum), 0)
    const widths = sizings.map((s) => {
      const share = flexTotal > 0 ? (s.flexible ? s.ideal / flexTotal : 0) : s.ideal / sumIdeal
      return s.ideal + leftover * share
    })
    return { widths, tableWidth: containerWidth }
  }
  if (available >= sumMin) {
    const deficit = sumIdeal - available
    const slackTotal = sumIdeal - sumMin
    const widths = sizings.map((s) =>
      slackTotal > 0 ? s.ideal - (deficit * (s.ideal - s.min)) / slackTotal : s.min
    )
    return { widths, tableWidth: containerWidth }
  }
  return { widths: sizings.map((s) => s.min), tableWidth: sumMin + selectColWidth }
}

/* ---- Composable ------------------------------------------------------------ */

/**
 * Bind measured, ratcheted column widths to a reactive column set, the
 * committed page rows and the scroll container's width.
 *
 * Rows must be the COMMITTED page (`props.items`), never the live crossfilter
 * drag rows — the ratchet makes widths hold still during a drag, and measuring
 * every drag frame would be wasted work.
 */
export function useColumnWidths(
  columns: Ref<MeasurableColumn[]>,
  rows: Ref<readonly Record<string, unknown>[]>,
  containerWidth: Ref<number>
): {
  columnWidths: ComputedRef<string[]>
  tableWidth: ComputedRef<string>
  useShortTitles: ComputedRef<boolean>
} {
  const fontsVersion = ref(fontsSettled ? 1 : 0)
  if (!fontsSettled && typeof document !== 'undefined' && 'fonts' in document) {
    const bump = (): void => {
      fontsVersion.value++
      fontSwapListeners.delete(bump)
    }
    fontSwapListeners.add(bump)
    onScopeDispose(() => fontSwapListeners.delete(bump))
  }

  // One ratchet per header mode: folding both modes into a single map would
  // either never let widths shrink on the long→short swap or throw away the
  // accumulated content widths on every threshold crossing.
  const createRatchet = () => {
    const map = new Map<string, ColumnSizing>()
    let currentSignature = ''
    return (signature: string, cols: MeasurableColumn[], fresh: ColumnSizing[]): ColumnSizing[] => {
      // Font swap or a different column set invalidates everything ratcheted.
      if (signature !== currentSignature) {
        map.clear()
        currentSignature = signature
      }
      return cols.map((column, index) => {
        const previous = map.get(column.key)
        const merged = previous
          ? {
              ideal: Math.max(previous.ideal, fresh[index].ideal),
              min: Math.max(previous.min, fresh[index].min),
              flexible: fresh[index].flexible
            }
          : fresh[index]
        map.set(column.key, merged)
        return merged
      })
    }
  }
  const ratchetLong = createRatchet()
  const ratchetShort = createRatchet()

  const longSizings = computed<ColumnSizing[]>(() => {
    const signature = `${fontsVersion.value}|${columns.value.map((c) => c.key).join(',')}`
    return ratchetLong(
      signature,
      columns.value,
      measureColumnIdeals(columns.value, rows.value, measureTableText)
    )
  })

  // Long↔short header switch: long titles render whenever their mins fit the
  // container; otherwise columns carrying a short label swap to it. The
  // decision reads only the long-title measurements (unaffected by which
  // labels actually render) and the container width (set by page layout, never
  // by table overflow), so it cannot feed back on itself — no hysteresis
  // needed. It is also page-stable: longSizings ride their ratchet, so paging
  // to narrower content can't flip short → long mid-session.
  const useShortTitles = computed<boolean>(() => {
    if (containerWidth.value <= 0) return false
    if (!columns.value.some((column) => column.shortTitle)) return false
    const sumMin = longSizings.value.reduce((sum, s) => sum + s.min, 0)
    return sumMin + SELECT_COL_WIDTH > containerWidth.value
  })

  // Only evaluated while short mode is active. The signature folds in the
  // short labels themselves: async dictionary arrival changes them and resets
  // this (empty until then) ratchet, while long↔short flips reuse it.
  const shortSizings = computed<ColumnSizing[]>(() => {
    const signature = `${fontsVersion.value}|${columns.value
      .map(({ key, shortTitle }) =>
        shortTitle ? `${key}=${shortTitle.isSymbol ? '!' : ''}${shortTitle.text}` : key
      )
      .join(',')}`
    return ratchetShort(
      signature,
      columns.value,
      measureColumnIdeals(columns.value, rows.value, measureTableText, true)
    )
  })

  const sizings = computed<ColumnSizing[]>(() =>
    useShortTitles.value ? shortSizings.value : longSizings.value
  )

  const distributed = computed(() => distributeWidths(sizings.value, containerWidth.value))
  const columnWidths = computed<string[]>(() =>
    distributed.value.widths.map((width) => `${width.toFixed(2)}px`)
  )
  const tableWidth = computed<string>(() => `${distributed.value.tableWidth.toFixed(2)}px`)
  return { columnWidths, tableWidth, useShortTitles }
}
