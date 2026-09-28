<script setup lang="ts">
import { ResidualStressNumberField, type ResidualStressField, type CountModel } from '@/backend'
import DoubleChart from '@/components/commons/charts/DoubleChart.vue'
import {
  doubleChartProps,
  getRequestFields,
  useDoubleChart,
  type ChartEmits
} from '@/composables/chart'
import { dashboardQueryKey } from '@/composables/dashboard'
import { useDataset } from '@/composables/useDataset'
import { RESIDUAL_KEY, fetchResiduals } from '@/components/residuals/data'
import { inject, toRef } from 'vue'

const props = defineProps(doubleChartProps<ResidualStressField>())

// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

// query via inject (not prop) so a filter change doesn't re-render this chart.
const query = inject(dashboardQueryKey, toRef(props, 'query'))
const { getCounts, countsSync, colorFor, getRange } = useDataset(RESIDUAL_KEY, fetchResiduals)
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
} = useDoubleChart<ResidualStressField, ResidualStressNumberField>(
  emit,
  props.fields,
  query,
  getCounts,
  {
    field: ResidualStressNumberField,
    getRange
  }
)
</script>

<template>
  <double-chart
    v-model:date-range="dateRange"
    v-model:number-range="numberRange"
    :animate="false"
    :color-for="colorForSecond"
    :all-counts="allCounts"
    :live-counts="getLiveCounts"
    :counts="counts"
    :date-max="dateMax"
    :date-min="dateMin"
    :fields="fields"
    label-prefix="residual."
    :number-max="numberMax"
    :number-min="numberMin"
    :type="props.type"
    @change:searches="changeSearches"
  />
</template>
