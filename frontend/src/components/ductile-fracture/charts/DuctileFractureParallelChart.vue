<script setup lang="ts">
import { DuctileFractureField, type DuctileFractureModel } from '@/backend'
import SimpleParallelChart from '@/components/commons/charts/SimpleParallelChart.vue'
import { parallelChartProps, useParallelChart, type ChartEmits } from '@/composables/chart'
import { dashboardQueryKey } from '@/composables/dashboard'
import { useDataset } from '@/composables/useDataset'
import { DUCTILE_FRACTURE_KEY, fetchDuctileFractures } from '@/components/ductile-fracture/data'
import { inject, toRef } from 'vue'

const props = defineProps(parallelChartProps<DuctileFractureField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

// query via inject (not prop) so a filter change doesn't re-render this chart.
const query = inject(dashboardQueryKey, toRef(props, 'query'))
const { getMatrix, matrixSync } = useDataset<DuctileFractureModel>(
  DUCTILE_FRACTURE_KEY,
  fetchDuctileFractures
)
const { changeSearches, data, ids, requestFields, isFiltered } =
  useParallelChart<DuctileFractureField>(
    emit,
    DuctileFractureField.Id,
    props.fields,
    query,
    getMatrix,
    matrixSync // live crossfilter drag frames (see useParallelChart)
  )
</script>

<template>
  <simple-parallel-chart
    :animate="false"
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
