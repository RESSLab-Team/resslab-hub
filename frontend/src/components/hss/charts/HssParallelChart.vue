<script setup lang="ts">
import { HSSColumnField } from '@/backend'
import SimpleParallelChart from '@/components/commons/charts/SimpleParallelChart.vue'
import { parallelChartProps, useParallelChart, type ChartEmits } from '@/composables/chart'
import { hssApi } from '@/plugins/axios'
import { toRef } from 'vue'

const props = defineProps(parallelChartProps<HSSColumnField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

const { changeSearches, data, ids, requestFields, isFiltered } = useParallelChart<HSSColumnField>(
  emit,
  HSSColumnField.Id,
  props.fields,
  toRef(props, 'query'),
  (fields, query) => hssApi.getHssColumnsMatrix(fields, query)
)
</script>

<template>
  <simple-parallel-chart
    :color="color"
    :data="data"
    :fields="fields"
    :ids="ids"
    :is-filtered="isFiltered"
    label-prefix="hss."
    :request-fields="requestFields"
    @change:searches="changeSearches"
  >
    <template #title>
      <slot name="title" />
    </template>
  </simple-parallel-chart>
</template>
