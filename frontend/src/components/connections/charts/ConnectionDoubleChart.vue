<script setup lang="ts">
import { ConnectionField, ConnectionNumberField } from '@/backend'
import DoubleChart from '@/components/commons/charts/DoubleChart.vue'
import { doubleChartProps, useDoubleChart, type ChartEmits } from '@/composables/chart'
import { connectionsApi } from '@/plugins/axios'
import { toRef } from 'vue'

const props = defineProps(doubleChartProps<ConnectionField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

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
} = useDoubleChart<ConnectionField, ConnectionNumberField>(
  emit,
  props.fields,
  toRef(props, 'query'),
  (fields, query) => connectionsApi.getConnectionsCounts(fields, query),
  {
    field: ConnectionNumberField,
    getRange: (field) => connectionsApi.getConnectionsRange(field)
  }
)
</script>

<template>
  <double-chart
    v-model:date-range="dateRange"
    v-model:number-range="numberRange"
    :all-counts="allCounts"
    :color="color"
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
