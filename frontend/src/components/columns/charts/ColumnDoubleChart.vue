<script setup lang="ts">
import { ColumnField, ColumnNumberField } from '@/backend'
import DoubleChart from '@/components/commons/charts/DoubleChart.vue'
import { doubleChartProps, useDoubleChart, type ChartEmits } from '@/composables/chart'
import { columnsApi } from '@/plugins/axios'
import { toRef } from 'vue'

const props = defineProps(doubleChartProps<ColumnField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

const { counts, changeSearches, dateMax, dateMin, dateRange, numberMax, numberMin, numberRange } =
  useDoubleChart<ColumnField, ColumnNumberField>(
    emit,
    props.fields,
    toRef(props, 'query'),
    (fields, query) => columnsApi.getColumnsCounts(fields, query),
    {
      field: ColumnNumberField,
      getRange: (field) => columnsApi.getColumnsRange(field)
    }
  )
</script>

<template>
  <double-chart
    v-model:date-range="dateRange"
    v-model:number-range="numberRange"
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
