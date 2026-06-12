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

export const debounceAPITime = 80
export const debounceAPIParameters = { leading: false, trailing: true }

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
