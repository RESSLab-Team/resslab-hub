/**
 * Filter auto-classification.
 *
 * Turns a database's data dictionary + its loaded rows into the list of filters
 * the rail should offer, so no dashboard has to hand-maintain one. The
 * dictionary `type` decides the broad shape (numeric / date / boolean / string)
 * and the *data* decides what a string column actually is: a short domain of
 * repeated values (checkbox list), or free text (search box).
 *
 * Pure and dependency-light on purpose — no Vue, no i18n, no stores — so the
 * heuristics can be unit-tested directly.
 */
import type { DictColumn } from '@/stores/dictionary'
import { range as numericRange } from '@/utils/aggregate'
import { formatValue, type Row } from '@/utils/queryEngine'
import { toBins, type BinData, type Count } from '@/utils/statistics'

export type FilterKind = 'categorical' | 'text' | 'numeric' | 'date' | 'boolean' | 'hidden'

/** Why a column got no filter — surfaced by the dev audit, never by the UI. */
export type HiddenReason = 'denylist' | 'unique' | 'url' | 'empty' | 'constant' | 'missing'

export interface FilterOption {
  /** Formatted value, as the query engine compares it (`'NA'` groups nulls). */
  value: string
  count: number
}

export interface FilterDescriptor {
  /** Column name — also the search key and the query-DSL field. */
  key: string
  column: DictColumn
  kind: FilterKind
  hiddenReason?: HiddenReason
  /** Distinct non-null values. */
  distinct: number
  nonNull: number
  /** Rows whose value is null/NaN — offered as the `NA` option. */
  missing: number
  /**
   * categorical + boolean + date: value → count, most frequent first.
   * text: only the most common values, as read-only context for the search box.
   */
  options?: FilterOption[]
  /** numeric: data bounds and the histogram (static, whole dataset). */
  min?: number
  max?: number
  bins?: BinData[]
  binEdges?: number[]
  /** date: ISO bounds. */
  dateMin?: string
  dateMax?: string
  /**
   * Set when a categorical column was demoted to text because its values carry
   * a query-DSL separator and could not be round-tripped through a filter value.
   */
  demoted?: boolean
}

/**
 * A string column with at most this many distinct values is a checkbox list.
 * Set generously: the list scrolls inside the row, so a long domain (steel
 * grades, section shapes) is still worth picking from rather than typing out.
 */
export const CATEGORICAL_MAX_DISTINCT = 25
/** …and only if its values actually repeat: distinct at most half the filled rows. */
export const CATEGORICAL_MAX_RATIO = 0.5
/** Near-unique string columns (specimen IDs, file paths) carry no signal. */
export const UNIQUE_RATIO = 0.95
/** …but only judge that once there are enough rows for the ratio to mean something. */
export const UNIQUE_MIN_ROWS = 20
/** Share of values that must look like links before the column is dropped. */
export const URL_RATIO = 0.9
/** How many recurring values a text column offers as search shortcuts. */
export const TEXT_TOP_VALUES = 8

/**
 * Columns nothing is ever filtered by, hidden by name whatever they contain:
 * identities and links, plus the map coordinates — `latitude`/`longitude` place
 * a specimen on the overview map, they are not a property of the test.
 */
const DENYLIST = /^(id|.*_id|link|url|doi|file_path|latitude|longitude)$/i
const URL_VALUE = /^https?:\/\//i
/** Values carrying one of these can't survive the query DSL as a filter value. */
const DSL_CHARS = /[,;]/

const NUMERIC_TYPES = new Set(['SmallInteger', 'Integer', 'BigInteger', 'Numeric', 'DecimalFloat'])

/** Missing-value sentinels produced by `formatValue` (null and NaN). */
const MISSING = new Set(['NA', 'NR'])
export const MISSING_OPTION = 'NA'

interface Accumulator {
  column: DictColumn
  /** Non-null formatted value → row count. */
  values: Map<string, number>
  missing: number
}

/**
 * Classify every dictionary column against the dataset.
 *
 * Columns keep their dictionary order. Hidden ones are returned too (with a
 * `hiddenReason`) so the dev audit can show what was dropped and why — the rail
 * filters them out itself.
 */
export function profileColumns(rows: Row[], columns: DictColumn[]): FilterDescriptor[] {
  const present = presentKeys(rows)
  const accumulators: Accumulator[] = []
  const descriptors = new Map<string, FilterDescriptor>()

  for (const column of columns) {
    if (!present.has(column.name)) {
      descriptors.set(column.name, hidden(column, 'missing'))
      continue
    }
    if (DENYLIST.test(column.name)) {
      descriptors.set(column.name, hidden(column, 'denylist'))
      continue
    }
    accumulators.push({ column, values: new Map(), missing: 0 })
  }

  // Rows outer / columns inner: each row object is touched once, and the ~70
  // property reads on it hit the same hidden class.
  for (const row of rows) {
    for (const accumulator of accumulators) {
      const formatted = formatValue(row[accumulator.column.name])
      if (MISSING.has(formatted)) {
        accumulator.missing += 1
        continue
      }
      accumulator.values.set(formatted, (accumulator.values.get(formatted) ?? 0) + 1)
    }
  }

  for (const accumulator of accumulators) {
    descriptors.set(accumulator.column.name, classify(rows, accumulator))
  }

  return columns.map((column) => descriptors.get(column.name) ?? hidden(column, 'missing'))
}

/** The filters the rail actually renders, in dictionary order. */
export function visibleFilters(descriptors: FilterDescriptor[]): FilterDescriptor[] {
  return descriptors.filter((descriptor) => descriptor.kind !== 'hidden')
}

function hidden(column: DictColumn, reason: HiddenReason): FilterDescriptor {
  return {
    key: column.name,
    column,
    kind: 'hidden',
    hiddenReason: reason,
    distinct: 0,
    nonNull: 0,
    missing: 0
  }
}

function classify(rows: Row[], accumulator: Accumulator): FilterDescriptor {
  const { column, values, missing } = accumulator
  const nonNull = rows.length - missing
  const base: FilterDescriptor = {
    key: column.name,
    column,
    kind: 'hidden',
    distinct: values.size,
    nonNull,
    missing
  }

  if (values.size === 0) return { ...base, hiddenReason: 'empty' }

  if (column.type === 'Boolean') {
    return { ...base, kind: 'boolean', options: sortOptions(values, missing) }
  }

  if (column.type === 'Date') {
    // Dictionary order is chronological for ISO dates, which is what the brush
    // and the bounds both want.
    const sorted = [...values.keys()].sort()
    return {
      ...base,
      kind: 'date',
      dateMin: sorted[0],
      dateMax: sorted[sorted.length - 1],
      options: sorted.map((value) => ({ value, count: values.get(value)! }))
    }
  }

  if (NUMERIC_TYPES.has(column.type)) {
    if (values.size < 2) return { ...base, hiddenReason: 'constant' }
    return { ...base, kind: 'numeric', ...histogram(rows, column.name, values) }
  }

  // String: the data decides.
  const distinctValues = [...values.keys()]
  const urls = distinctValues.filter((value) => URL_VALUE.test(value)).length
  if (urls >= URL_RATIO * distinctValues.length) return { ...base, hiddenReason: 'url' }

  if (values.size >= UNIQUE_RATIO * nonNull && nonNull >= UNIQUE_MIN_ROWS) {
    return { ...base, hiddenReason: 'unique' }
  }

  const categorical =
    values.size <= CATEGORICAL_MAX_DISTINCT && values.size <= CATEGORICAL_MAX_RATIO * nonNull
  if (!categorical) return { ...base, kind: 'text', options: topValues(values) }

  // A value containing `,` or `;` can't be sent through the query DSL (they
  // separate set members and clauses), so such a column falls back to search.
  if (distinctValues.some((value) => DSL_CHARS.test(value))) {
    return { ...base, kind: 'text', demoted: true, options: topValues(values) }
  }

  return { ...base, kind: 'categorical', options: sortOptions(values, missing) }
}

/**
 * Bin a numeric column exactly the way the dashboards' double charts do
 * (`toBins`, Sturges over the aggregated counts), so a rail histogram and a
 * chart histogram of the same field line up.
 */
function histogram(
  rows: Row[],
  field: string,
  values: Map<string, number>
): Pick<FilterDescriptor, 'min' | 'max' | 'bins' | 'binEdges'> {
  const counts: Count[] = []
  for (const [value, count] of values) {
    const numeric = Number(value)
    if (!isNaN(numeric)) counts.push({ name: '', value: numeric, count })
  }
  // RangeModel carries nullable bounds (an empty column has none); by here the
  // column has at least two distinct values, so `?? 0` never actually fires.
  const bounds = numericRange(rows, field)
  const min = bounds.min ?? 0
  const max = bounds.max ?? 0
  if (counts.length === 0) return { min, max }
  const bins = toBins([''], counts)[0].data
  // Boundaries [e0…eN]: the first bin's left edge then every bin's right edge.
  const binEdges = bins.length ? [bins[0][2], ...bins.map((bin) => bin[3])] : undefined
  return { min, max, bins, binEdges }
}

/**
 * The most common values of a free-text column, as search shortcuts. Omitted
 * when nothing recurs — a list of singletons is noise, not a distribution.
 */
function topValues(values: Map<string, number>): FilterOption[] | undefined {
  const options = sortOptions(values, 0).slice(0, TEXT_TOP_VALUES)
  return options[0]?.count > 1 ? options : undefined
}

/** Most frequent first; the missing-value bucket always sorts last. */
function sortOptions(values: Map<string, number>, missing: number): FilterOption[] {
  const options = [...values.entries()]
    .map(([value, count]) => ({ value, count }))
    .sort((a, b) => b.count - a.count || a.value.localeCompare(b.value))
  if (missing > 0) options.push({ value: MISSING_OPTION, count: missing })
  return options
}

/**
 * Which column names the rows actually carry. Sampled rather than taken from
 * `rows[0]` alone, so a dictionary column stays visible even when the first
 * records happen to omit it.
 */
function presentKeys(rows: Row[]): Set<string> {
  const keys = new Set<string>()
  for (const row of rows.slice(0, 20)) {
    for (const key of Object.keys(row)) keys.add(key)
  }
  return keys
}
