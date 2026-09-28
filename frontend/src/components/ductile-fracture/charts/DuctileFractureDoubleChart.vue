<script setup lang="ts">
import {
  DuctileFractureField,
  DuctileFractureNumberField,
  type CountModel,
  type DuctileFractureModel
} from '@/backend'
import DoubleChart from '@/components/commons/charts/DoubleChart.vue'
import {
  doubleChartProps,
  getRequestFields,
  useDoubleChart,
  type ChartEmits
} from '@/composables/chart'
import { dashboardQueryKey } from '@/composables/dashboard'
import { useDataset } from '@/composables/useDataset'
import { DUCTILE_FRACTURE_KEY, fetchDuctileFractures } from '@/components/ductile-fracture/data'
import { inject, toRef } from 'vue'

const props = defineProps(doubleChartProps<DuctileFractureField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

// query via inject (not prop) so a filter change doesn't re-render this chart.
const query = inject(dashboardQueryKey, toRef(props, 'query'))
const { getCounts, countsSync, colorFor, getRange } = useDataset<DuctileFractureModel>(
  DUCTILE_FRACTURE_KEY,
  fetchDuctileFractures
)
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
} = useDoubleChart<DuctileFractureField, DuctileFractureNumberField>(
  emit,
  props.fields,
  query,
  getCounts,
  {
    field: DuctileFractureNumberField,
    getRange
  }
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
    label-prefix="ductile_fracture."
    :number-max="numberMax"
    :number-min="numberMin"
    :type="props.type"
    @change:searches="changeSearches"
  />
</template>
