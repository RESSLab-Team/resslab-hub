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

export type FieldType = 'string' | 'number' | 'date' | 'boolean'
export type FieldTypes = Record<string, FieldType>
export type Row = Record<string, unknown>

type RowPredicate = (row: Row) => boolean
type ValuePredicate = (value: unknown) => boolean

const ISO_DATE = /^\d{4}-\d{2}-\d{2}/

/** Infer a field-type map from the dataset (first defined value per field). */
export function inferFieldTypes(rows: Row[]): FieldTypes {
  const types: FieldTypes = {}
  for (const row of rows) {
    for (const key of Object.keys(row)) {
      if (types[key]) continue
      const value = row[key]
      if (value === null || value === undefined) continue
      if (typeof value === 'number') types[key] = 'number'
      else if (typeof value === 'boolean') types[key] = 'boolean'
      else if (typeof value === 'string' && ISO_DATE.test(value)) types[key] = 'date'
      else types[key] = 'string'
    }
  }
  return types
}

// Single-entry memo: during a crossfilter drag every chart on a dashboard filters
// with the SAME query string against the SAME dataset each frame, so remembering
// the last compiled predicate turns ~9 parses (and regex compiles) per frame into
// one. Keyed on the exact (query, fieldTypes) pair — fieldTypes is a stable
// per-dataset object, so an identity check is enough; any other input recompiles.
let memoQuery: string | undefined
let memoTypes: FieldTypes | undefined
let memoPredicate: RowPredicate | undefined

/** Compile a query string into a reusable per-row predicate (parsed once). */
export function compileQuery(query: string | undefined, fieldTypes: FieldTypes): RowPredicate {
  if (!query) return () => true
  if (query === memoQuery && fieldTypes === memoTypes && memoPredicate) return memoPredicate
  const clauses = query
    .split(queryFieldSeparator)
    .filter((clause) => clause.length > 0)
    .map((clause) => compileClause(clause, fieldTypes))
  const predicate: RowPredicate = (row) => clauses.every((p) => p(row))
  memoQuery = query
  memoTypes = fieldTypes
  memoPredicate = predicate
  return predicate
}

// Filtered-result memo (single entry, same reasoning as the predicate memo):
// during a drag frame every chart AND the table filter the same rows with the
// same query, so remembering the last result turns ~10 O(n) passes per frame
// into one. Identity-keyed on the rows array; callers never mutate the result
// (they map/slice/copy-sort it), so sharing one array is safe.
let memoRows: Row[] | undefined
let memoFilterQuery: string | undefined
let memoFilterTypes: FieldTypes | undefined
let memoFiltered: Row[] | undefined

/** Filter rows by a query string, compiling the predicate once. */
export function filterRows<T extends Row>(
  rows: T[],
  query: string | undefined,
  fieldTypes: FieldTypes
): T[] {
  if (!query) return rows
  if (rows === memoRows && query === memoFilterQuery && fieldTypes === memoFilterTypes) {
    return memoFiltered as T[]
  }
  const predicate = compileQuery(query, fieldTypes)
  const filtered = rows.filter(predicate)
  memoRows = rows
  memoFilterQuery = query
  memoFilterTypes = fieldTypes
  memoFiltered = filtered
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
  return (row) => predicate(row[key])
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
    return (value) => !inner(value)
  }
  if (expression.includes(',')) {
    const set = new Set(expression.split(','))
    return (value) => set.has(formatValue(value))
  }
  // Exact match (`=value`). Client-side only, like the derived-ratio keys: a
  // single-value selection in the filter rail must not behave like the default
  // substring match, or picking `RBS` would also keep `RBS-b` rows. Multi-value
  // selections already match exactly through the ',' branch above.
  if (expression.startsWith('=')) {
    const target = expression.slice(1)
    return (value) => formatValue(value) === target
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
