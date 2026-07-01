<script setup lang="ts">
import {
  MaterialDateField,
  MaterialField,
  MaterialNumberField,
  type CountModel,
  type MaterialModel
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
import { MATERIAL_KEY, fetchMaterials } from '@/components/materials/data'
import { inject, toRef } from 'vue'

const props = defineProps(doubleChartProps<MaterialField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

// query via inject (not prop) so a filter change doesn't re-render this chart.
const query = inject(dashboardQueryKey, toRef(props, 'query'))
const { getCounts, countsSync, getRange, getDateRange } = useDataset<MaterialModel>(
  MATERIAL_KEY,
  fetchMaterials
)

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
} = useDoubleChart<MaterialField, MaterialNumberField, MaterialDateField>(
  emit,
  props.fields,
  query,
  getCounts,
  {
    field: MaterialNumberField,
    getRange
  },
  {
    field: MaterialDateField,
    getRange: getDateRange
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
    :color="color"
    :counts="counts"
    :date-max="dateMax"
    :date-min="dateMin"
    :fields="fields"
    label-prefix="material."
    :number-max="numberMax"
    :number-min="numberMin"
    :type="props.type"
    @change:searches="changeSearches"
  />
</template>
