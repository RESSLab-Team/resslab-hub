<script setup lang="ts">
import { ColumnField } from '@/backend'
import SimpleParallelChart from '@/components/commons/charts/SimpleParallelChart.vue'
import { parallelChartProps, useParallelChart, type ChartEmits } from '@/composables/chart'
import { columnsApi } from '@/plugins/axios'
import { toRef } from 'vue'

const props = defineProps(parallelChartProps<ColumnField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

const { changeSearches, data, ids, requestFields } = useParallelChart<ColumnField>(
  emit,
  ColumnField.Id,
  props.fields,
  toRef(props, 'query'),
  (fields, query) => columnsApi.getColumnsMatrix(fields, query)
)
</script>

<template>
  <simple-parallel-chart
    :color="color"
    :data="data"
    :fields="fields"
    :ids="ids"
    label-prefix="column."
    :request-fields="requestFields"
    @change:searches="changeSearches"
  />
</template>
