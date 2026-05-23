<script setup lang="ts">
import { DuctileFractureField } from '@/backend'
import SimpleParallelChart from '@/components/commons/charts/SimpleParallelChart.vue'
import { parallelChartProps, useParallelChart, type ChartEmits } from '@/composables/chart'
import { ductileFractureApi } from '@/plugins/axios'
import { toRef } from 'vue'

const props = defineProps(parallelChartProps<DuctileFractureField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

const { changeSearches, data, ids, requestFields, isFiltered } =
  useParallelChart<DuctileFractureField>(
    emit,
    DuctileFractureField.Id,
    props.fields,
    toRef(props, 'query'),
    (fields, query) => ductileFractureApi.getDuctileFracturesMatrix(fields, query)
  )
</script>

<template>
  <simple-parallel-chart
    :color="color"
    :data="data"
    :fields="fields"
    :ids="ids"
    :is-filtered="isFiltered"
    label-prefix="ductile_fracture."
    :request-fields="requestFields"
    @change:searches="changeSearches"
  />
</template>
