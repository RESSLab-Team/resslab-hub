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

/**
 * Return `url` only if it is a safe, navigable link (http/https or a
 * root-relative/fragment path). Database-sourced `link`/`url` fields are
 * rendered into anchor `href`s, so a value like `javascript:…` would otherwise
 * execute on click. Unsafe or unparseable values yield `undefined`, causing Vue
 * to omit the `href` attribute entirely.
 */
export function safeHref(url: string | null | undefined): string | undefined {
  if (!url) return undefined
  const trimmed = url.trim()
  if (trimmed.startsWith('/') || trimmed.startsWith('#')) return trimmed
  try {
    const { protocol } = new URL(trimmed, window.location.origin)
    if (protocol === 'http:' || protocol === 'https:') return trimmed
  } catch {
    return undefined
  }
  return undefined
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
