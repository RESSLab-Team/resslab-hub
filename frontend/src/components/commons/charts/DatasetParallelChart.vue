<script setup lang="ts" generic="F extends string">
// The dashboard parallel-coordinates view bound to its dataset. `source` says
// which dataset, from `components/{type}/data.ts`.
import SimpleParallelChart from '@/components/commons/charts/SimpleParallelChart.vue'
import {
  useParallelChart,
  type ChartEmits,
  type DatasetSource,
  type ParallelField
} from '@/composables/chart'
import { dashboardQueryKey } from '@/composables/dashboard'
import { useDataset } from '@/composables/useDataset'
import { inject, toRef } from 'vue'

const props = defineProps<{
  source: DatasetSource<F>
  fields: NoInfer<ParallelField<F>[]>
  query?: string
}>()
const emit = defineEmits<ChartEmits>()

// query via inject (not prop) so a filter change doesn't re-render this chart.
const query = inject(
  dashboardQueryKey,
  toRef(() => props.query)
)
const { getMatrix, matrixSync } = useDataset(props.source.key, props.source.fetchAll)
const {
  changeSearches,
  commitSelection,
  data,
  highlightIds,
  ids,
  publishSelection,
  requestFields,
  isFiltered,
  zoomed
} = useParallelChart<F>(
  emit,
  props.source.idField,
  props.fields,
  query,
  getMatrix,
  matrixSync // live crossfilter drag frames (see useParallelChart)
)
</script>

<template>
  <simple-parallel-chart
    v-model:zoomed="zoomed"
    :animate="false"
    :highlight-ids="highlightIds"
    :data="data"
    :fields="fields"
    :ids="ids"
    :is-filtered="isFiltered"
    :label-prefix="source.labelPrefix"
    :request-fields="requestFields"
    @brush:commit="commitSelection"
    @brush:live="publishSelection"
    @change:searches="changeSearches"
  />
</template>
