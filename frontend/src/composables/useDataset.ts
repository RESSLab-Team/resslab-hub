/**
 * In-browser dataset cache + query layer.
 *
 * Fetches a dashboard's whole (small, <200 kB) dataset once, caches it in
 * memory, and answers the chart/table data requests locally with the pure
 * `queryEngine` / `aggregate` helpers — instead of one server round-trip per
 * chart per filter change.
 *
 * The returned functions keep the exact `Promise<AxiosResponse<...>>` shape of
 * the generated API client, so they drop straight into the existing
 * `useSingleChart` / `useDoubleChart` / `useParallelChart` / `useTable`
 * composables in place of the injected `connectionsApi.*` lambdas.
 *
 * Loading is deduped per key: every chart on a dashboard triggers the same
 * in-flight fetch, so a dashboard visit costs a single network request.
 */
import type { CountModel, MatrixModel, RangeModel } from '@/backend'
import { counts, matrix, range, totalCount } from '@/utils/aggregate'
import type { Page } from '@/utils/backend'
import { filterRows, inferFieldTypes, type FieldTypes, type Row } from '@/utils/queryEngine'
import type { AxiosResponse } from 'axios'

interface DatasetEntry {
  rows: Row[]
  fieldTypes: FieldTypes
  ready: Promise<void>
}

const cache = new Map<string, DatasetEntry>()

function ensure(key: string, fetchAll: () => Promise<Row[]>): DatasetEntry {
  const existing = cache.get(key)
  if (existing) return existing
  const entry: DatasetEntry = { rows: [], fieldTypes: {}, ready: Promise.resolve() }
  entry.ready = fetchAll().then((rows) => {
    entry.rows = rows
    entry.fieldTypes = inferFieldTypes(rows)
  })
  cache.set(key, entry)
  return entry
}

function asResponse<T>(data: T): AxiosResponse<T> {
  return { data } as unknown as AxiosResponse<T>
}

function compare(a: unknown, b: unknown): number {
  if (a === b) return 0
  if (a === null || a === undefined) return 1 // nulls / undefined sort last
  if (b === null || b === undefined) return -1
  if (typeof a === 'number' && typeof b === 'number') return a - b
  return String(a).localeCompare(String(b))
}

function sortRows(rows: Row[], sortBy?: string[], sortDesc?: boolean[]): Row[] {
  if (!sortBy || sortBy.length === 0) return rows
  return [...rows].sort((a, b) => {
    for (let i = 0; i < sortBy.length; i++) {
      const direction = sortDesc?.[i] ? -1 : 1
      const comparison = compare(a[sortBy[i]], b[sortBy[i]])
      if (comparison !== 0) return comparison * direction
    }
    return 0
  })
}

/**
 * Bind the local dataset engine for one dashboard.
 *
 * @param key       cache key (one per dashboard, e.g. `'connection'`)
 * @param fetchAll  fetches the complete dataset once
 * @param idField   identity field used for the parallel-coordinates matrix
 */
export function useDataset<M extends { id: string }>(
  key: string,
  fetchAll: () => Promise<M[]>,
  idField = 'id'
) {
  const load = () => ensure(key, fetchAll as unknown as () => Promise<Row[]>)

  async function getCounts(
    fields?: string[],
    query?: string
  ): Promise<AxiosResponse<CountModel[]>> {
    const entry = load()
    await entry.ready
    return asResponse(counts(filterRows(entry.rows, query, entry.fieldTypes), fields ?? []))
  }

  // Synchronous counts for the crossfilter drag path: the dataset is already in
  // memory by the time a user is dragging, so a brush frame can recompute its
  // aggregate inline (no promise, no microtask) and repaint imperatively. Returns
  // [] if the dataset hasn't loaded yet — the reactive path covers that case.
  function countsSync(fields: string[], query?: string): CountModel[] {
    const entry = load()
    if (!entry.rows.length) return []
    return counts(filterRows(entry.rows, query, entry.fieldTypes), fields)
  }

  async function getTotal(): Promise<AxiosResponse<CountModel[]>> {
    const entry = load()
    await entry.ready
    return asResponse(totalCount(entry.rows))
  }

  async function getRange(field: string): Promise<AxiosResponse<RangeModel>> {
    const entry = load()
    await entry.ready
    return asResponse(range(entry.rows, field))
  }

  async function getMatrix(fields: string[], query?: string): Promise<AxiosResponse<MatrixModel>> {
    const entry = load()
    await entry.ready
    return asResponse(matrix(filterRows(entry.rows, query, entry.fieldTypes), idField, fields))
  }

  // Synchronous matrix for the crossfilter drag path (see countsSync).
  function matrixSync(fields: string[], query?: string): MatrixModel {
    const entry = load()
    if (!entry.rows.length) return { ids: [], data: [] } as unknown as MatrixModel
    return matrix(filterRows(entry.rows, query, entry.fieldTypes), idField, fields)
  }

  // Synchronous filtered row count for the crossfilter drag path. The table's rows
  // are far too heavy to re-render per frame (Vuetify data-table row patch is
  // ~40-70ms — a long task on its own), so during a drag we update ONLY the count
  // (a cheap footer update, no row patch) and let the rows settle on pointer-up.
  function countRowsSync(query?: string): number {
    const entry = load()
    if (!entry.rows.length) return 0
    return filterRows(entry.rows, query, entry.fieldTypes).length
  }

  async function getPage(
    query?: string,
    sortBy?: string[],
    sortDesc?: boolean[],
    page?: number,
    size?: number
  ): Promise<AxiosResponse<Page<M>>> {
    const entry = load()
    await entry.ready
    const filtered = filterRows(entry.rows, query, entry.fieldTypes)
    const sorted = sortRows(filtered, sortBy, sortDesc)
    const pageNumber = page ?? 1
    const pageSize = size && size > 0 ? size : sorted.length
    const start = (pageNumber - 1) * pageSize
    const items = sorted.slice(start, start + pageSize) as unknown as M[]
    return asResponse({ items, total: filtered.length, page: pageNumber, size: pageSize })
  }

  return {
    getCounts,
    countsSync,
    getTotal,
    getRange,
    getMatrix,
    matrixSync,
    countRowsSync,
    getPage,
    ready: () => load().ready
  }
}
