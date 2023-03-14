<script setup lang="ts">
import { MaterialField } from '@/backend'
import SimpleParallelChart from '@/components/commons/charts/SimpleParallelChart.vue'
import { parallelChartProps, useParallelChart, type ChartEmits } from '@/composables/chart'
import { materialsApi } from '@/plugins/axios'
import { toRef } from 'vue'

const props = defineProps(parallelChartProps<MaterialField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

const { changeSearches, data, ids, requestFields } = useParallelChart<MaterialField>(
  emit,
  MaterialField.Id,
  props.fields,
  toRef(props, 'query'),
  (fields, query) => materialsApi.getMaterialsMatrix(fields, query)
)
</script>

<template>
  <simple-parallel-chart
    :color="color"
    :data="data"
    :fields="fields"
    :ids="ids"
    label-prefix="material."
    :request-fields="requestFields"
    @change:searches="changeSearches"
  />
</template>
