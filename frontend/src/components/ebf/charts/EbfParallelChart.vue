<script setup lang="ts">
import { EccentricBracedFrameField } from '@/backend'
import SimpleParallelChart from '@/components/commons/charts/SimpleParallelChart.vue'
import { parallelChartProps, useParallelChart, type ChartEmits } from '@/composables/chart'
import { ebfApi } from '@/plugins/axios'
import { toRef } from 'vue'

const props = defineProps(parallelChartProps<EccentricBracedFrameField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

const { changeSearches, data, ids, requestFields, isFiltered } =
  useParallelChart<EccentricBracedFrameField>(
    emit,
    EccentricBracedFrameField.Id,
    props.fields,
    toRef(props, 'query'),
    (fields, query) => ebfApi.getEccentricBracedFramesMatrix(fields, query)
  )
</script>

<template>
  <simple-parallel-chart
    :color="color"
    :data="data"
    :fields="fields"
    :ids="ids"
    :is-filtered="isFiltered"
    label-prefix="ebf."
    :request-fields="requestFields"
    @change:searches="changeSearches"
  >
    <template #title>
      <slot name="title" />
    </template>
  </simple-parallel-chart>
</template>
