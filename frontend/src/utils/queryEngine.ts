/**
 * Client-side query engine.
 *
 * Mirrors the backend predicate semantics (`Component.__get_where_clause` /
 * `__get_predicate` in `backend/resslab_hub/utils/common.py`) so that a filter
 * query string — the exact same one the dashboards used to send to the API — can
 * be evaluated against an in-memory array of rows in the browser.
 *
 * The query grammar (built in `composables/dashboard.ts`):
 *   clauses are joined by ';' (logical AND)
 *   a clause is either
 *     - `key:expression`  → a predicate on that field, or
 *     - `expression`      → a global search across every field.
 *   expressions: leading '!' negates; ',' → value-in-set; leading '=' → exact
 *   match; '<<' → inclusive range; leading '<'/'>' → numeric compare; otherwise
 *   substring (string), equality (number/boolean) or SQL ilike wildcard matching.
 */
import { queryFieldSeparator, queryKeyValueSeparator } from '@/composables/dashboard'
import { missingKey } from '@/utils/missing'

export type FieldType = 'string' | 'number' | 'date' | 'boolean'
export type FieldTypes = Record<string, FieldType>
export type Row = Record<string, unknown>

type RowPredicate = (row: Row) => boolean
/** `row` and `key` let an exact or set match tell `NR` from `NA` (#427). */
type ValuePredicate = (value: unknown, row?: Row, key?: string) => boolean

const ISO_DATE = /^\d{4}-\d{2}-\d{2}/

/** Infer a field-type map from the dataset (first defined value per field). */
export function inferFieldTypes(rows: Row[]): FieldTypes {
  const types: FieldTypes = {}
  for (const row of rows) {
    for (const key of Object.keys(row)) {
      if (types[key]) continue
      const value = row[key]
      if (value === null || value === undefined) continue
      // A list (the `not_reported` names, #427) is not a field you can query,
      // and the global search must not match column names in it, like the API.
      if (Array.isArray(value)) continue
      if (typeof value === 'number') types[key] = 'number'
      else if (typeof value === 'boolean') types[key] = 'boolean'
      else if (typeof value === 'string' && ISO_DATE.test(value)) types[key] = 'date'
      else types[key] = 'string'
    }
  }
  return types
}

// Memo capacity. A dashboard drag frame asks for more than one distinct query:
// every chart and the table filter on the committed query, while the parallel
// chart strips its own clause (`stripOwned` in composables/chart.ts) and so asks
// for a second string. A single-entry memo ping-pongs between the two and misses
// on every call; a handful of slots makes the hit rate order-independent.
// The filter rail adds one string per active filter: an open row counts its
// values with all the filters but its own (#329). The cached arrays only hold
// references to the same row objects, so a slot costs little.
const MEMO_CAPACITY = 24

const TRUE_PREDICATE: RowPredicate = () => true

// Least-recently-used helpers over an insertion-ordered Map: re-inserting on a
// hit moves the key to the back, so the first key is always the coldest one.
function lruGet<V>(memo: Map<string, V>, key: string): V | undefined {
  const hit = memo.get(key)
  if (hit !== undefined) {
    memo.delete(key)
    memo.set(key, hit)
  }
  return hit
}

function lruSet<V>(memo: Map<string, V>, key: string, value: V): void {
  memo.set(key, value)
  if (memo.size > MEMO_CAPACITY) memo.delete(memo.keys().next().value as string)
}

// Compiled-predicate memo: during a crossfilter drag the dashboard re-parses the
// same few query strings against the same dataset every frame, and parsing is
// the expensive half (a RegExp per clause). Keyed by fieldTypes identity — a
// stable per-dataset object — so each dataset gets its own memo and a reloaded
// one starts empty instead of needing explicit invalidation.
const predicateMemos = new WeakMap<FieldTypes, Map<string, RowPredicate>>()

/** Compile a query string into a reusable per-row predicate (parsed once). */
export function compileQuery(query: string | undefined, fieldTypes: FieldTypes): RowPredicate {
  if (!query) return TRUE_PREDICATE
  let memo = predicateMemos.get(fieldTypes)
  if (!memo) {
    memo = new Map()
    predicateMemos.set(fieldTypes, memo)
  }
  const cached = lruGet(memo, query)
  if (cached) return cached
  const clauses = query
    .split(queryFieldSeparator)
    .filter((clause) => clause.length > 0)
    .map((clause) => compileClause(clause, fieldTypes))
  const predicate: RowPredicate = (row) => clauses.every((p) => p(row))
  lruSet(memo, query, predicate)
  return predicate
}

// Filtered-result memo (same reasoning as the predicate memo): every chart and
// the table run the same O(n) pass each frame, so caching the result collapses
// ~10 passes into one per distinct query. Keyed by rows-array identity, which
// also makes a dataset reload self-invalidating. Stable identities matter beyond
// the scan itself: the sort memo in composables/useDataset.ts and the matrix
// memo in utils/aggregate.ts both key off the array returned here.
// Callers must never mutate a result — they map/slice/copy-sort it — since up to
// MEMO_CAPACITY arrays are now shared per dataset.
const filterMemos = new WeakMap<Row[], { types: FieldTypes; byQuery: Map<string, Row[]> }>()

/** Filter rows by a query string, compiling the predicate once. */
export function filterRows<T extends Row>(
  rows: T[],
  query: string | undefined,
  fieldTypes: FieldTypes
): T[] {
  if (!query) return rows
  let entry = filterMemos.get(rows)
  // Guard against a caller pairing the same rows with different field types:
  // drop the cached results rather than returning ones compiled from the old map.
  if (!entry || entry.types !== fieldTypes) {
    entry = { types: fieldTypes, byQuery: new Map() }
    filterMemos.set(rows, entry)
  }
  const cached = lruGet(entry.byQuery, query)
  if (cached) return cached as T[]
  const filtered = rows.filter(compileQuery(query, fieldTypes))
  lruSet(entry.byQuery, query, filtered)
  return filtered
}

function compileClause(clause: string, fieldTypes: FieldTypes): RowPredicate {
  const separatorIndex = clause.indexOf(queryKeyValueSeparator)
  if (separatorIndex === -1) {
    return compileGlobal(clause, fieldTypes)
  }
  const key = clause.slice(0, separatorIndex)
  const expression = clause.slice(separatorIndex + 1)
  // Derived-ratio clause (`a/b:expression`): a parallel-chart brush on a
  // division axis filters on the quotient of two numeric columns. Client-side
  // only — this grammar extension never reaches the backend.
  if (fieldTypes[key] === undefined && key.includes('/')) {
    const [dividend, divisor] = key.split('/', 2)
    if (fieldTypes[dividend] !== undefined && fieldTypes[divisor] !== undefined) {
      const predicate = compilePredicate(expression, 'number')
      return (row) => predicate(Number(row[dividend]) / Number(row[divisor]))
    }
  }
  const predicate = compilePredicate(expression, fieldTypes[key] ?? 'string')
  return (row) => predicate(row[key], row, key)
}

/**
 * Global search across every field. Mirrors `__get_global_predicate`: the
 * expression already carries the SQL wildcards (`%value%`) added by the query
 * builder, and a leading '!' negates the whole ORed match.
 */
function compileGlobal(expression: string, fieldTypes: FieldTypes): RowPredicate {
  const negate = expression.startsWith('!')
  const pattern = negate ? expression.slice(1) : expression
  const regex = ilikeToRegExp(pattern)
  const fields = Object.keys(fieldTypes)
  // Backend ORs the per-column match (or per-column non-match when negated),
  // so the negation lives inside the `some`, not around it.
  return (row) =>
    fields.some((field) => {
      const matches = regex.test(toText(row[field]))
      return negate ? !matches : matches
    })
}

/** Compile a single `expression` into a value predicate, in backend order. */
function compilePredicate(expression: string, type: FieldType): ValuePredicate {
  if (expression.startsWith('!')) {
    const inner = compilePredicate(expression.slice(1), type)
    return (value, row, key) => !inner(value, row, key)
  }
  // Exact match (`=value`). Client-side only, like the derived-ratio keys: a
  // single-value selection in the filter rail must not behave like the default
  // substring match, or picking `RBS` would also keep `RBS-b` rows. It comes before
  // the set, because the value can hold a comma: `=Fell, Kanvinde` is one value. A
  // set never starts with `=`, it is the bare values joined by commas.
  if (expression.startsWith('=')) {
    const target = expression.slice(1)
    return (value, row, key) => keyOf(value, row, key) === target
  }
  if (expression.includes(',')) {
    const set = new Set(expression.split(','))
    return (value, row, key) => set.has(keyOf(value, row, key))
  }
  if (expression.includes('<<')) {
    const [min, max] = expression.split('<<')
    if (type === 'date') {
      const lo = Date.parse(min)
      const hi = Date.parse(max)
      return (value) => {
        const time = Date.parse(toText(value))
        return time >= lo && time <= hi
      }
    }
    const lo = Number(min)
    const hi = Number(max)
    return (value) => {
      const numeric = Number(value)
      return numeric >= lo && numeric <= hi
    }
  }
  if (expression.startsWith('<')) {
    const bound = Number(expression.slice(1))
    return (value) => Number(value) < bound
  }
  if (expression.startsWith('>')) {
    const bound = Number(expression.slice(1))
    return (value) => Number(value) > bound
  }
  switch (type) {
    case 'number': {
      const target = Number(expression)
      return (value) => Number(value) === target
    }
    case 'boolean': {
      const target = parseBool(expression)
      return (value) => Boolean(value) === target
    }
    case 'date':
      return (value) => toText(value) === expression
    default: {
      // String column: backend wraps as ilike(`%expression%`), so `%`/`_` in
      // the expression itself act as wildcards too (e.g. option `exterior%`).
      const regex = ilikeToRegExp(`%${expression}%`)
      return (value) => regex.test(toText(value))
    }
  }
}

/** Format a value the way the backend `__format_value` + `str()` would. */
/**
 * Like `formatValue(row[field])`, but an empty cell gives `NR` when the row
 * lists the field as not reported and `NA` otherwise (#427). The filters, the
 * chart counts and the table all group on this key, so they agree.
 */
export function cellKey(row: Row, field: string): string {
  const value = row[field]
  if (value === null || value === undefined) return missingKey(row, field)
  return formatValue(value)
}

function keyOf(value: unknown, row: Row | undefined, key: string | undefined): string {
  if ((value === null || value === undefined) && row && key) return missingKey(row, key)
  return formatValue(value)
}

export function formatValue(value: unknown): string {
  if (value === null || value === undefined) return 'NA'
  if (typeof value === 'number') return Number.isNaN(value) ? 'NR' : String(value)
  if (typeof value === 'boolean') return value ? 'True' : 'False'
  return String(value)
}

function toText(value: unknown): string {
  return value === null || value === undefined ? '' : String(value)
}

/** Convert an SQL ilike pattern (`%` = any, `_` = one) to a case-insensitive RegExp. */
function ilikeToRegExp(pattern: string): RegExp {
  let source = '^'
  for (const char of pattern) {
    if (char === '%') source += '.*'
    else if (char === '_') source += '.'
    else source += char.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  }
  source += '$'
  return new RegExp(source, 'i')
}

/** Mirror Python's distutils `strtobool` truthy set (defaulting to false). */
function parseBool(value: string): boolean {
  return ['true', '1', 'yes', 'y', 't', 'on'].includes(value.trim().toLowerCase())
}
