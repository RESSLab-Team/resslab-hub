<script setup lang="ts" generic="F extends string">
// A dashboard histogram (bar or line) bound to its dataset, with the number or
// date brush on its first field. `source` says which dataset, from
// `components/{type}/data.ts`.
import type { CountModel } from '@/backend'
import DoubleChart from '@/components/commons/charts/DoubleChart.vue'
import {
  getRequestFields,
  useDoubleChart,
  type ChartEmits,
  type DatasetSource,
  type DoubleFields
} from '@/composables/chart'
import { dashboardQueryKey } from '@/composables/dashboard'
import { useDataset } from '@/composables/useDataset'
import { inject, toRef } from 'vue'

const props = defineProps<{
  source: DatasetSource<F>
  fields: NoInfer<DoubleFields<F>>
  type?: 'bar' | 'line'
  query?: string
}>()
const emit = defineEmits<ChartEmits>()

// query via inject (not prop) so a filter change doesn't re-render this chart.
const query = inject(
  dashboardQueryKey,
  toRef(() => props.query)
)
const { getCounts, countsSync, colorFor, getRange, getDateRange } = useDataset(
  props.source.key,
  props.source.fetchAll
)
// Stable reference: a fresh closure per render would re-render the chart for nothing.
const colorForSecond = colorFor(getRequestFields(props.fields)[1])

// Synchronous counts for the crossfilter drag path, bound to this chart's request
// fields so DoubleChart can repaint imperatively (off Vue's reactivity) mid-drag.
const getLiveCounts = (liveQuery?: string): CountModel[] =>
  countsSync(getRequestFields(props.fields), liveQuery)
const {
  counts,
  allCounts,
  changeSearches,
  dateMax,
  dateMin,
  dateRange,
  numberMax,
  numberMin,
  numberRange
} = useDoubleChart<F, string, string>(
  emit,
  props.fields,
  query,
  getCounts,
  { field: props.source.numberFields, getRange },
  props.source.dateFields ? { field: props.source.dateFields, getRange: getDateRange } : undefined
)
</script>

<template>
  <double-chart
    v-model:date-range="dateRange"
    v-model:number-range="numberRange"
    :animate="false"
    :all-counts="allCounts"
    :live-counts="getLiveCounts"
    :color-for="colorForSecond"
    :counts="counts"
    :date-max="dateMax"
    :date-min="dateMin"
    :fields="fields"
    :label-prefix="source.labelPrefix"
    :number-max="numberMax"
    :number-min="numberMin"
    :type="type"
    @change:searches="changeSearches"
  />
</template>
