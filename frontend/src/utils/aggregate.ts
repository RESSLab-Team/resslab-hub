/**
 * Client-side aggregators.
 *
 * Pure functions producing the exact response shapes the dashboards' chart
 * endpoints return, computed from an in-memory array of rows. They mirror the
 * backend aggregations in `backend/resslab_hub/utils/common.py`:
 *   `get_counts`  → GROUP BY field(s), COUNT      → `counts`
 *   `get_range`   → MIN/MAX of a numeric column   → `range`
 *   `get_matrix`  → per-row id + fields (no group) → `matrix`
 */
import type { CountModel, DateRangeModel, MatrixModel, RangeModel } from '@/backend'
import { formatValue, type Row } from '@/utils/queryEngine'
import { extent } from 'd3-array'

// Control char so multi-field group keys can't collide with values that
// contain spaces (e.g. `["a b","c"]` vs `["a","b c"]`).
const KEY_SEPARATOR = '\u0000'

/**
 * GROUP BY the given field(s) and count rows per group, matching
 * `get_counts`: `names` holds the string-formatted group key(s).
 */
export function counts(rows: Row[], fields: string[]): CountModel[] {
  const groups = new Map<string, CountModel>()
  for (const row of rows) {
    const names = fields.map((field) => formatValue(row[field]))
    const key = names.join(KEY_SEPARATOR)
    const existing = groups.get(key)
    if (existing) existing.value += 1
    else groups.set(key, { names, value: 1 })
  }
  return [...groups.values()]
}

/** Total row count as a single group — matches `get_counts` with no fields. */
export function totalCount(rows: Row[]): CountModel[] {
  return [{ names: [], value: rows.length }]
}

/** MIN/MAX of a numeric field across the given rows (`get_range`). */
export function range(rows: Row[], field: string): RangeModel {
  const [min, max] = extent(rows, (row) => toNumber(row[field]))
  return { min: min ?? 0, max: max ?? 0 }
}

/** MIN/MAX of a date field across the given rows (`get_date_range`). */
export function dateRange(rows: Row[], field: string): DateRangeModel {
  const [min, max] = extent(rows, (row) => {
    const value = row[field]
    return value === null || value === undefined ? undefined : String(value)
  })
  return { min: min ?? '', max: max ?? '' }
}

/**
 * Per-row id + field values for the parallel-coordinates chart (`get_matrix`).
 * NaN numbers collapse to null, matching the backend's `__clean_value`.
 */
export function matrix(rows: Row[], idField: string, fields: string[]): MatrixModel {
  const ids = rows.map((row) => String(row[idField]))
  const data = rows.map((row) => fields.map((field) => cleanValue(row[field])))
  // MatrixModel.data is a generated placeholder type (`DataInnerInner`); the
  // chart consumer casts it to `(string | number)[][]`, so cast here too.
  return { ids, data: data as unknown as MatrixModel['data'] }
}

function toNumber(value: unknown): number | undefined {
  if (value === null || value === undefined) return undefined
  const numeric = Number(value)
  return Number.isNaN(numeric) ? undefined : numeric
}

function cleanValue(value: unknown): string | number | null {
  if (value === null || value === undefined) return null
  if (typeof value === 'number') return Number.isNaN(value) ? null : value
  if (typeof value === 'boolean') return value ? 'True' : 'False'
  return String(value)
}
