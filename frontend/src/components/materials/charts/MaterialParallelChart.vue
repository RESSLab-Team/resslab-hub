<script setup lang="ts">
import { MaterialField, type MaterialModel } from '@/backend'
import SimpleParallelChart from '@/components/commons/charts/SimpleParallelChart.vue'
import { parallelChartProps, useParallelChart, type ChartEmits } from '@/composables/chart'
import { dashboardQueryKey } from '@/composables/dashboard'
import { useDataset } from '@/composables/useDataset'
import { MATERIAL_KEY, fetchMaterials } from '@/components/materials/data'
import { inject, toRef } from 'vue'

const props = defineProps(parallelChartProps<MaterialField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

// query via inject (not prop) so a filter change doesn't re-render this chart.
const query = inject(dashboardQueryKey, toRef(props, 'query'))
const { getMatrix, matrixSync } = useDataset<MaterialModel>(MATERIAL_KEY, fetchMaterials)
const { changeSearches, data, ids, requestFields, isFiltered } = useParallelChart<MaterialField>(
  emit,
  MaterialField.Id,
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
    label-prefix="material."
    :request-fields="requestFields"
    @change:searches="changeSearches"
  />
</template>
