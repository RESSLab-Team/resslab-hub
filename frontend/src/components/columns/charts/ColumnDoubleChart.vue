<script setup lang="ts">
import { ColumnField, ColumnNumberField, type CountModel } from '@/backend'
import DoubleChart from '@/components/commons/charts/DoubleChart.vue'
import {
  doubleChartProps,
  getRequestFields,
  useDoubleChart,
  type ChartEmits
} from '@/composables/chart'
import { dashboardQueryKey } from '@/composables/dashboard'
import { useDataset } from '@/composables/useDataset'
import { COLUMN_KEY, fetchColumns } from '@/components/columns/data'
import { inject, toRef } from 'vue'

const props = defineProps(doubleChartProps<ColumnField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

// query via inject (not prop) so a filter change doesn't re-render this chart.
const query = inject(dashboardQueryKey, toRef(props, 'query'))
const { getCounts, countsSync, getRange } = useDataset(COLUMN_KEY, fetchColumns)

// Synchronous counts for the crossfilter drag path — bound to this chart's request
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
} = useDoubleChart<ColumnField, ColumnNumberField>(emit, props.fields, query, getCounts, {
  field: ColumnNumberField,
  getRange
})
</script>

<template>
  <double-chart
    v-model:date-range="dateRange"
    v-model:number-range="numberRange"
    :animate="false"
    :all-counts="allCounts"
    :live-counts="getLiveCounts"
    :color="color"
    :counts="counts"
    :date-max="dateMax"
    :date-min="dateMin"
    :fields="fields"
    label-prefix="column."
    :number-max="numberMax"
    :number-min="numberMin"
    :type="props.type"
    @change:searches="changeSearches"
  />
</template>
