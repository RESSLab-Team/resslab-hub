<script setup lang="ts">
import { ConnectionField } from '@/backend'
import SimpleParallelChart from '@/components/commons/charts/SimpleParallelChart.vue'
import { parallelChartProps, useParallelChart, type ChartEmits } from '@/composables/chart'
import { connectionsApi } from '@/plugins/axios'
import { toRef } from 'vue'

const props = defineProps(parallelChartProps<ConnectionField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

const { changeSearches, data, ids, requestFields, isFiltered } = useParallelChart<ConnectionField>(
  emit,
  ConnectionField.Id,
  props.fields,
  toRef(props, 'query'),
  (fields, query) => connectionsApi.getConnectionsMatrix(fields, query)
)
</script>

<template>
  <simple-parallel-chart
    :color="color"
    :data="data"
    :fields="fields"
    :ids="ids"
    :is-filtered="isFiltered"
    label-prefix="connection."
    :request-fields="requestFields"
    @change:searches="changeSearches"
  >
    <template #title>
      <slot name="title" />
    </template>
  </simple-parallel-chart>
</template>
