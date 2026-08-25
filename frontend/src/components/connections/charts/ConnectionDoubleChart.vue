<script setup lang="ts">
import { ConnectionField, ConnectionNumberField, type CountModel } from '@/backend'
import DoubleChart from '@/components/commons/charts/DoubleChart.vue'
import {
  doubleChartProps,
  getRequestFields,
  useDoubleChart,
  type ChartEmits
} from '@/composables/chart'
import { dashboardQueryKey } from '@/composables/dashboard'
import { useDataset } from '@/composables/useDataset'
import { CONNECTION_KEY, fetchConnections } from '@/components/connections/data'
import { inject, toRef } from 'vue'

const props = defineProps(doubleChartProps<ConnectionField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

// query via inject (not prop) so a filter change doesn't re-render this chart.
const query = inject(dashboardQueryKey, toRef(props, 'query'))
const { getCounts, countsSync, colorFor, getRange } = useDataset(CONNECTION_KEY, fetchConnections)
// Stable reference: a fresh closure per render would re-render the chart for nothing.
const colorForSecond = colorFor(getRequestFields(props.fields)[1])

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
} = useDoubleChart<ConnectionField, ConnectionNumberField>(emit, props.fields, query, getCounts, {
  field: ConnectionNumberField,
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
    :color-for="colorForSecond"
    :counts="counts"
    :date-max="dateMax"
    :date-min="dateMin"
    :fields="fields"
    label-prefix="connection."
    :number-max="numberMax"
    :number-min="numberMin"
    :type="props.type"
    @change:searches="changeSearches"
  />
</template>
