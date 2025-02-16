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
