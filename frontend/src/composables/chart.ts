import type { CountModel, DateRangeModel, MatrixModel, RangeModel } from '@/backend'
import type { Value } from '@/utils/common'
import { debounceAPIParameters, debounceAPITime } from '@/utils/common'
import type { Color } from '@/utils/vuetify'
import type { AxiosResponse } from 'axios'
import { chain, debounce } from 'lodash'
import { computed, ref, watch, type Ref } from 'vue'
import { queryFieldSeparator, queryKeyValueSeparator } from './dashboard'
const chartProps = {
  color: Object as () => Color,
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

// Single

export interface Count {
  name: string
  value: number
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
  const counts = ref<Count[]>([])

  function changeSearches(key: string, value?: Value) {
    emit('change:searches', key, value)
  }

  const debouncedGetCounts = debounce(
    () =>
      getCounts([field], query.value)
        .then((response) => response.data)
        .then((values) => {
          counts.value = values
            .map((count) => {
              return {
                name: count.names[0],
                value: count.value
              }
            })
            .sort((c1, c2) => (c1.name < c2.name ? -1 : 1))
        }),
    debounceAPITime,
    debounceAPIParameters
  )

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

  const counts = ref<CountModel[]>([])
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
          counts.value = values
        }),
    debounceAPITime,
    debounceAPIParameters
  )

  watch(
    query,
    (newQuery, oldQuery) => {
      if (newQuery !== oldQuery) debouncedGetCounts()
    },
    { immediate: true }
  )

  const numberField = getField<NF>(numberRangeOption.field, fields[0].toString())
  if (numberField) {
    numberRangeOption
      .getRange(numberField)
      .then((response) => response.data)
      .then((range) => {
        numberMin.value = range.min
        numberMax.value = range.max
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
function getRequestFields<F>(fields: DoubleFields<F>): [F, F] {
  const secondField: DoubleField<F> = fields[1]
  if (typeof secondField === 'object') {
    return [fields[0], (secondField as MappingField<F>).id]
  } else {
    return [fields[0], secondField]
  }
}

// Parallel

export interface ParallelField<T = string> {
  id: T | Division<T>
  name?: string
  mapping?: Map<string, string>
}
export interface Division<T> {
  dividend: T
  divisor: T
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
  getMatrix: (fields: F[], query?: string) => Promise<AxiosResponse<MatrixModel>>
) {
  const ids = ref<string[]>([])
  const data = ref<(string | number)[][]>([])

  const requestFields = computed<F[]>(() =>
    chain(fields)
      .flatMap((f) => {
        if (typeof f.id === 'string') {
          return [f.id]
        } else {
          return [f.id.dividend, f.id.divisor]
        }
      })
      .uniq()
      .value()
  )

  function changeSearches(value?: Value) {
    emit('change:searches', idField, value)
  }

  const debouncedGetMatrix = debounce(
    () =>
      getMatrix(requestFields.value, query.value)
        .then((response) => response.data)
        .then((matrixModel) => {
          ids.value = matrixModel.ids
          data.value = matrixModel.data as (string | number)[][]
        }),
    debounceAPITime,
    debounceAPIParameters
  )

  watch(
    query,
    (newQuery, oldQuery) => {
      if (newQuery !== oldQuery) debouncedGetMatrix()
    },
    { immediate: true }
  )
  const isFiltered = computed(() => query.value?.includes(idField) ?? false)

  return { ids, data, requestFields, isFiltered, changeSearches }
}
