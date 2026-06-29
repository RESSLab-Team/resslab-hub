<script setup lang="ts">
import { MaterialDateField, MaterialField, MaterialNumberField } from '@/backend'
import DoubleChart from '@/components/commons/charts/DoubleChart.vue'
import { doubleChartProps, useDoubleChart, type ChartEmits } from '@/composables/chart'
import { materialsApi } from '@/plugins/axios'
import { toRef } from 'vue'

const props = defineProps(doubleChartProps<MaterialField>())
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
} = useDoubleChart<MaterialField, MaterialNumberField, MaterialDateField>(
  emit,
  props.fields,
  toRef(props, 'query'),
  (fields, query) => materialsApi.getMaterialsCounts(fields, query),
  {
    field: MaterialNumberField,
    getRange: (field) => materialsApi.getMaterialsRange(field)
  },
  {
    field: MaterialDateField,
    getRange: (field) => materialsApi.getMaterialsDateRange(field)
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
    label-prefix="material."
    :number-max="numberMax"
    :number-min="numberMin"
    :type="props.type"
    @change:searches="changeSearches"
  />
</template>
