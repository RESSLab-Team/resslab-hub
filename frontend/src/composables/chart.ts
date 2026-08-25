import type { CountModel, DateRangeModel, MatrixModel, RangeModel } from '@/backend'
import type { Value } from '@/utils/common'
import { debounceAPIParameters, debounceDataTime } from '@/utils/common'
import type { AxiosResponse } from 'axios'
import { chain, debounce } from 'lodash'
import { computed, onScopeDispose, ref, shallowRef, watch, type Ref } from 'vue'
import { publishLive, publishSettle, subscribeCrossfilter } from './crossfilterBus'
import { queryFieldSeparator, queryKeyValueSeparator } from './dashboard'
import { cancelScheduled, scheduleFrameUpdate } from './frameScheduler'

// Unique per chart instance, so the frame scheduler can coalesce repeated
// updates from the same chart (latest-wins) without conflating separate charts.
let chartInstanceId = 0
const chartProps = {
  query: String
}

export interface ChartEmits {
  (e: 'change:searches', key: string, value?: Value): void
}

function getSearchValueFromQuery(query: string | undefined, field: string): string | undefined {
  if (!query) {
    return undefined
  }
  const entry = query
    .split(queryFieldSeparator)
    .find((f) => f.startsWith(field + queryKeyValueSeparator))
  if (!entry) {
    return undefined
  }
  const [, value] = entry.split(queryKeyValueSeparator, 2)
  return value
}

/** Replace (or drop, when `value` is undefined) a field's clause in a query string. */
export function spliceQueryClause(
  query: string | undefined,
  field: string,
  value?: string
): string | undefined {
  const clauses = query ? query.split(queryFieldSeparator) : []
  const kept = clauses.filter((clause) => !clause.startsWith(field + queryKeyValueSeparator))
  if (value) kept.push(`${field}${queryKeyValueSeparator}${value}`)
  return kept.length ? kept.join(queryFieldSeparator) : undefined
}

// Single

export interface Count {
  name: string
  value: number
}

/**
 * Map/sort raw counts into the shape `useSingleChart`'s reactive `counts` holds.
 * Exported for the crossfilter wrappers: building their live drag frames through
 * the same function keeps them pixel-identical to the committed render.
 */
export function toSingleCounts(values: CountModel[]): Count[] {
  return values
    .map((count) => ({ name: count.names[0], value: count.value }))
    .sort((c1, c2) => (c1.name < c2.name ? -1 : 1))
}

export function singleChartProps<F extends string>() {
  return {
    ...chartProps,
    showReset: {
      type: Boolean as unknown as () => boolean,
      required: false as false
    },
    field: {
      type: String as unknown as () => F,
      required: true as true
    },
    flat: {
      type: Boolean as unknown as () => boolean,
      required: false as false
    }
  }
}
export function useSingleChart<F>(
  emit: ChartEmits,
  field: F,
  query: Ref<string | undefined>,
  getCounts: (fields?: F[], query?: string) => Promise<AxiosResponse<CountModel[]>>
) {
  // shallowRef throughout: these arrays are always replaced wholesale (never
  // mutated in place), so deep reactivity would only add proxy overhead that
  // the chart option computeds pay on every filter tick.
  const counts = shallowRef<Count[]>([])
  const updateKey = `chart-${chartInstanceId++}`

  function changeSearches(key: string, value?: Value) {
    emit('change:searches', key, value)
  }

  const debouncedGetCounts = debounce(
    () =>
      getCounts([field], query.value)
        .then((response) => response.data)
        .then((values) => {
          const next = toSingleCounts(values)
          // Stagger the write so N charts don't all flush in one long task.
          scheduleFrameUpdate(updateKey, () => (counts.value = next))
        }),
    debounceDataTime,
    debounceAPIParameters
  )
  // A trailing debounce fire or queued frame task must not write refs of a
  // disposed component.
  onScopeDispose(() => {
    debouncedGetCounts.cancel()
    cancelScheduled(updateKey)
  })

  watch(
    query,
    (newQuery, oldQuery) => {
      if (newQuery !== oldQuery) debouncedGetCounts()
    },
    { immediate: true }
  )

  return { counts, changeSearches }
}

// Double

export type DoubleFields<F = string> = [F, DoubleField<F>]
export type DoubleField<F = string> = F | MappingField<F>
export interface MappingField<T> {
  id: T
  mapping: Map<string, string>
}
export interface RangeOption<F, M> {
  field: Record<string, F>
  getRange: (numberField: F) => Promise<AxiosResponse<M>>
}

export function doubleChartProps<F extends string>() {
  return {
    ...chartProps,
    fields: {
      type: Array as unknown as () => DoubleFields<F>,
      required: true as true
    },
    type: String as () => 'bar' | 'line'
  }
}
export function useDoubleChart<F extends string, NF extends string, DF extends string = string>(
  emit: ChartEmits,
  fields: DoubleFields<F>,
  query: Ref<string | undefined>,
  getCounts: (fields?: F[], query?: string) => Promise<AxiosResponse<CountModel[]>>,
  numberRangeOption: RangeOption<NF, RangeModel>,
  dateRangeOption?: RangeOption<DF, DateRangeModel>
) {
  const requestFields = getRequestFields(fields)

  const counts = shallowRef<CountModel[]>([])
  const updateKey = `chart-${chartInstanceId++}`
  // Full unfiltered counts for the distribution brush background — must stay
  // constant regardless of the active filter so the shape never shrinks.
  const allCounts = shallowRef<CountModel[]>([])
  const dateMin = ref<string>()
  const dateMax = ref<string>()
  const dateRange = ref<[string, string]>()
  const numberMin = ref<number>()
  const numberMax = ref<number>()
  const numberRange = ref<[number, number]>()

  function fetchQuery(query: string | undefined) {
    const value = getSearchValueFromQuery(query, fields[0])
    if (!value) {
      numberRange.value = undefined
      dateRange.value = undefined
    } else {
      const minMax = value.split('<<', 2) as [string, string]
      const [numberMin, numberMax] = minMax.map((v) => Number(v))
      if (!isNaN(numberMin) && !isNaN(numberMax)) {
        numberRange.value = [numberMin, numberMax]
      } else {
        dateRange.value = minMax
      }
    }
  }

  watch(query, fetchQuery, { immediate: true })

  function changeSearches(key: string, value?: Value) {
    emit('change:searches', key, value)
  }

  const debouncedGetCounts = debounce(
    () =>
      getCounts(requestFields, query.value)
        .then((response) => response.data)
        .then((values) => {
          scheduleFrameUpdate(updateKey, () => (counts.value = values))
        }),
    debounceDataTime,
    debounceAPIParameters
  )

  // Fetch once, without any query filter, to build the stable distribution.
  const debouncedGetAllCounts = debounce(
    () =>
      getCounts(requestFields, undefined)
        .then((response) => response.data)
        .then((values) => {
          allCounts.value = values
        }),
    debounceDataTime,
    debounceAPIParameters
  )
  // A trailing debounce fire or queued frame task must not write refs of a
  // disposed component.
  onScopeDispose(() => {
    debouncedGetCounts.cancel()
    debouncedGetAllCounts.cancel()
    cancelScheduled(updateKey)
  })

  watch(
    query,
    (newQuery, oldQuery) => {
      if (newQuery !== oldQuery) debouncedGetCounts()
    },
    { immediate: true }
  )

  // allCounts only needs to be fetched once (unfiltered, stable per chart).
  debouncedGetAllCounts()

  const numberField = getField<NF>(numberRangeOption.field, fields[0].toString())
  if (numberField) {
    numberRangeOption
      .getRange(numberField)
      .then((response) => response.data)
      .then((range) => {
        numberMin.value = range.min ?? undefined
        numberMax.value = range.max ?? undefined
      })
  }
  if (dateRangeOption) {
    const dateField = getField<DF>(dateRangeOption.field, fields[0].toString())
    if (dateField) {
      dateRangeOption
        .getRange(dateField)
        .then((response) => response.data)
        .then((range) => {
          dateMin.value = range.min
          dateMax.value = range.max
        })
    }
  }

  return {
    counts,
    allCounts,
    dateMin,
    dateMax,
    dateRange,
    numberMin,
    numberMax,
    numberRange,
    changeSearches
  }
}

function getField<F extends string>(f: Record<string, F>, field: string): F | undefined {
  return Object.values<F>(f).find((numberField) => field === numberField.toString())
}
export function getRequestFields<F>(fields: DoubleFields<F>): [F, F] {
  const secondField: DoubleField<F> = fields[1]
  if (typeof secondField === 'object') {
    return [fields[0], (secondField as MappingField<F>).id]
  } else {
    return [fields[0], secondField]
  }
}

// Parallel

export interface ParallelField<T = string> {
  id: T | Division<T> | Computed<T>
  name?: string
  mapping?: Map<string, string>
  sortValues?: string[]
}
export interface Division<T> {
  dividend: T
  divisor: T
}
export interface Computed<T> {
  key: string
  fields: T[]
  compute: (values: (number | null)[]) => number | null
}

/**
 * What a parallel brush selects. `clauses` maps plain-field axes to query
 * expressions (`min<<max` ranges, `a,b` value sets) — the preferred form, since
 * it commits meaningful column filters. `ids` is the fallback when the brush
 * touches a derived axis (division/computed) that no column clause can express.
 */
export type ParallelSelection =
  | { clauses: Record<string, string>; ids?: undefined }
  | { ids: string[]; clauses?: undefined }

export function isDivision<T>(id: T | Division<T> | Computed<T>): id is Division<T> {
  return typeof id === 'object' && id !== null && 'dividend' in id
}
export function isComputed<T>(id: T | Division<T> | Computed<T>): id is Computed<T> {
  return typeof id === 'object' && id !== null && 'compute' in id
}

export function parallelChartProps<F extends string>() {
  return {
    ...chartProps,
    fields: {
      type: Array as () => ParallelField<F>[],
      required: true as true
    }
  }
}
export function useParallelChart<F extends string>(
  emit: ChartEmits,
  idField: F,
  fields: ParallelField<F>[],
  query: Ref<string | undefined>,
  getMatrix: (fields: F[], query?: string) => Promise<AxiosResponse<MatrixModel>>,
  // Optional crossfilter drag source. When given, a live drag frame recomputes
  // the matrix synchronously from the in-memory dataset and feeds the same
  // reactive ids/data refs. Deliberately reactive (unlike the bar charts): the
  // per-frame cost is the N-polyline canvas redraw either way, and it leaves the
  // chart's brush-select machinery untouched. The commit refreshes on pointer-up.
  matrixSync?: (fields: F[], query?: string) => MatrixModel
) {
  const ids = shallowRef<string[]>([])
  const data = shallowRef<(string | number)[][]>([])
  const updateKey = `chart-${chartInstanceId++}`

  const requestFields = computed<F[]>(() =>
    chain(fields)
      .flatMap((f) => {
        if (typeof f.id === 'string') {
          return [f.id]
        } else if (isDivision(f.id)) {
          return [f.id.dividend, f.id.divisor]
        } else {
          return f.id.fields
        }
      })
      .uniq()
      .value()
  )

  function changeSearches(value?: Value) {
    // A trailing comma turns a single id into the query engine's exact
    // set-membership instead of substring ilike — 'Specimen_1' must not also
    // match 'Specimen_10'.
    const exact =
      typeof value === 'string' && value.length > 0 && !value.includes(',') ? `${value},` : value
    emit('change:searches', idField, exact)
  }

  // Fields whose query clause this chart's brush currently owns (committed or
  // mid-drag). Owned clauses are excluded from the chart's own data query —
  // classic crossfilter self-exclusion: the brush origin keeps showing the full
  // domain, so the bands stay meaningful and committing doesn't collapse the
  // chart under the user's pointer. The id clause (line click / derived-axis
  // fallback) is always treated as owned.
  const ownedFields = ref<string[]>([])
  let ownedClauses: Record<string, string> = {}

  // "Zoom to selection": while zoomed the chart drops self-exclusion and shows
  // exactly what the committed query filters — the same rows as the table.
  const zoomed = ref(false)

  // Ids selected by this chart's committed id clause (line click / derived-axis
  // fallback) — the component paints them as the red overlay.
  const highlightIds = computed<string[]>(() => {
    const value = getSearchValueFromQuery(query.value, idField)
    return value ? value.split(',').filter((id) => id.length > 0) : []
  })

  const ownQuery = computed(() => {
    if (zoomed.value) return query.value
    let stripped = spliceQueryClause(query.value, idField)
    for (const field of ownedFields.value) stripped = spliceQueryClause(stripped, field)
    return stripped
  })

  const debouncedGetMatrix = debounce(
    () =>
      getMatrix(requestFields.value, ownQuery.value)
        .then((response) => response.data)
        .then((matrixModel) => {
          const nextIds = matrixModel.ids
          const nextData = matrixModel.data as (string | number)[][]
          scheduleFrameUpdate(updateKey, () => {
            ids.value = nextIds
            data.value = nextData
          })
        }),
    debounceDataTime,
    debounceAPIParameters
  )
  // A trailing debounce fire or queued frame task must not write refs of a
  // disposed component.
  onScopeDispose(() => {
    debouncedGetMatrix.cancel()
    cancelScheduled(updateKey)
  })

  // Watching the *stripped* query dedupes for free: commits that only touch the
  // id clause (this chart's own selection) leave ownQuery unchanged → no refetch.
  // Initial fetch is explicit — an unfiltered ownQuery is undefined, which the
  // `newQuery !== oldQuery` guard of an immediate watch would mistake for "no change".
  watch(ownQuery, (newQuery, oldQuery) => {
    if (newQuery !== oldQuery) debouncedGetMatrix()
  })
  debouncedGetMatrix()

  function stripOwned(fromQuery: string | undefined): string | undefined {
    let stripped = spliceQueryClause(fromQuery, idField)
    for (const field of ownedFields.value) stripped = spliceQueryClause(stripped, field)
    return stripped
  }

  if (matrixSync) {
    // `false` = no live frame seen this gesture (distinct from a real undefined query).
    let lastLive: string | undefined | false = false
    const unsubscribe = subscribeCrossfilter({
      onLive: (liveQuery) => {
        // Same self-exclusion as the fetch path; also swallows this chart's own
        // brush frames (only owned clauses change → the stripped query is stable).
        const stripped = zoomed.value ? liveQuery : stripOwned(liveQuery)
        if (stripped === lastLive) return
        lastLive = stripped
        const model = matrixSync(requestFields.value, stripped)
        ids.value = model.ids
        data.value = model.data as unknown as (string | number)[][]
      },
      onSettle: () => {
        lastLive = false
      }
    })
    onScopeDispose(unsubscribe)
  }

  /** Live drag frame: the current query with the brush's clauses spliced in. */
  function publishSelection(selection: ParallelSelection) {
    // Adopt ownership of the brushed fields up front so this chart's own live
    // frames (and the eventual commit) don't refilter it by its own brush.
    if (!selection.ids) ownedFields.value = Object.keys(selection.clauses ?? {})
    let live = stripOwned(query.value)
    if (selection.ids) {
      live = spliceQueryClause(
        live,
        idField,
        selection.ids.length ? selection.ids.join(',') : undefined
      )
    } else {
      for (const [field, value] of Object.entries(selection.clauses ?? {})) {
        live = spliceQueryClause(live, field, value)
      }
    }
    publishLive(live)
  }

  /** Drag ended: commit the brush through Vue (once), then settle the bus. */
  function commitSelection(selection: ParallelSelection) {
    const nextClauses: Record<string, string> = selection.ids ? {} : { ...selection.clauses }
    // Explicit undefined for anything owned before and gone now — and the full
    // current set every time, so an externally overwritten clause self-heals.
    for (const field of Object.keys(ownedClauses)) {
      if (!(field in nextClauses)) emit('change:searches', field, undefined)
    }
    for (const [field, value] of Object.entries(nextClauses)) {
      emit('change:searches', field, value)
    }
    changeSearches(selection.ids?.length ? selection.ids.join(',') : undefined)
    ownedClauses = nextClauses
    ownedFields.value = Object.keys(nextClauses)
    publishSettle()
  }

  // Filtered by this chart's own selection: the id clause (line click / derived
  // fallback) or any owned brush clause still present in the query.
  const isFiltered = computed(() => {
    const currentQuery = query.value
    if (!currentQuery) return false
    if (getSearchValueFromQuery(currentQuery, idField) !== undefined) return true
    return ownedFields.value.some(
      (field) => getSearchValueFromQuery(currentQuery, field) !== undefined
    )
  })

  // The last owned clause was removed externally (e.g. another cell's "remove
  // filter") — release ownership so the chart filters normally again.
  watch(isFiltered, (filtered) => {
    if (!filtered) {
      ownedClauses = {}
      ownedFields.value = []
    }
  })

  return {
    ids,
    data,
    requestFields,
    isFiltered,
    changeSearches,
    publishSelection,
    commitSelection,
    zoomed,
    highlightIds
  }
}
