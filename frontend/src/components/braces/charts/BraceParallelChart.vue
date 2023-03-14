<script setup lang="ts">
import { BraceField } from '@/backend'
import SimpleParallelChart from '@/components/commons/charts/SimpleParallelChart.vue'
import { parallelChartProps, useParallelChart, type ChartEmits } from '@/composables/chart'
import { bracesApi } from '@/plugins/axios'
import { toRef } from 'vue'

const props = defineProps(parallelChartProps<BraceField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

const { changeSearches, data, ids, requestFields } = useParallelChart<BraceField>(
  emit,
  BraceField.Id,
  props.fields,
  toRef(props, 'query'),
  (fields, query) => bracesApi.getBracesMatrix(fields, query)
)
</script>

<template>
  <simple-parallel-chart
    :color="color"
    :data="data"
    :fields="fields"
    :ids="ids"
    label-prefix="brace."
    :request-fields="requestFields"
    @change:searches="changeSearches"
  />
</template>
