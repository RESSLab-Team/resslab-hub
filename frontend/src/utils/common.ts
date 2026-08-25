export type Value = boolean | number | string | (string | null)[]
export type Searches = Record<string, Value>

export function sum(a: number, b: number): number {
  return a + b
}

export function filterColumnValue(value: Value): boolean {
  if (value === null) {
    return false
  }
  if (typeof value === 'string' || Array.isArray(value)) {
    return value.length > 0
  } else {
    return true
  }
}

/** Minimal translator shape, so this module stays free of the i18n plugin
 *  (which reads localStorage at import time). */
export type Translate = (key: string, named?: Record<string, unknown>) => string

/**
 * A filter value, rendered for a chip or a collapsed rail row.
 *
 * Mirrors the query grammar: `<<` is a range, an array (or a comma list) is a
 * value set, and a leading `=` marks an exact match — a detail of the DSL, not
 * something to show the user.
 */
export function formatFilterValue(value: Value, t: Translate): string {
  if (Array.isArray(value)) {
    return t('commons.n_selected', { n: value.length })
  }
  if (typeof value === 'boolean') {
    return value ? t('commons.yes') : t('commons.no')
  }
  const text = String(value)
  if (text.includes('<<')) {
    return text.split('<<', 2).join(' – ')
  }
  if (text.startsWith('=')) {
    return text.slice(1)
  }
  return text.includes(',') ? t('commons.n_selected', { n: text.split(',').length }) : text
}

/**
 * Whether a filter value was written in the structured grammar the rail's
 * inputs emit — an exact match (`=value`), a value set (array) or a range
 * (`lo<<hi`) — as opposed to the bare text a typed filter box holds. Where a
 * column offers both inputs, this decides which one owns the value.
 */
export function isStructuredFilterValue(value: Value | undefined): boolean {
  if (value === undefined || value === null || value === '') return false
  if (Array.isArray(value)) return value.length > 0
  const text = String(value)
  return text.startsWith('=') || text.includes('<<')
}

export const publicPath: string = import.meta.env.BASE_URL ?? ''

export const globalSearchKey = 'search'

export interface Section {
  id: string
  bf: number
  h: number
  tf: number
  tw: number
  ix: number
  zx: number
  ry: number
  d: number
  a: number
  iy: number
}

export interface HSSSection {
  id: string
  zy: number
  iy: number
  b: number
  t: number
  h: number
}

// URL-sync coalescing (router.replace churn during typing) — see useDashboard.
// Not on the data path any more.
export const debounceAPITime = 80
// Data-path wait: every dashboard computes results in-browser now, so there is
// no request to sit on — 0 keeps lodash-debounce's burst coalescing (calls in
// the same tick still fold into leading + one trailing) with no timer lag.
export const debounceDataTime = 0
// Fire on the LEADING edge: the first filter action of a burst runs immediately
// (instant feel) instead of waiting out the window, while a rapid burst still
// coalesces to leading + one trailing.
export const debounceAPIParameters = { leading: true, trailing: true }

/**
 * Share the current view URL (filters round-trip through the router query):
 * native share sheet when available, else clipboard, else a notification link.
 */
export function shareCurrentUrl(
  fullPath: string,
  notify: (message: string, url?: string) => void
): void {
  const url = new URL(window.location.origin + fullPath).href
  if (navigator.share) {
    navigator.share({ url })
    return
  }
  if (navigator.clipboard) {
    navigator.clipboard.writeText(url)
    notify('Copied to clipboard')
    return
  }
  notify(url, url)
}
