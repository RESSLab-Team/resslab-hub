<script setup lang="ts">
import { EccentricBracedFrameField } from '@/backend'
import SimpleParallelChart from '@/components/commons/charts/SimpleParallelChart.vue'
import { parallelChartProps, useParallelChart, type ChartEmits } from '@/composables/chart'
import { subscribeCrossfilter } from '@/composables/crossfilterBus'
import { dashboardQueryKey } from '@/composables/dashboard'
import { useDataset } from '@/composables/useDataset'
import { EBF_KEY, fetchEbfs } from '@/components/ebf/data'
import { inject, onUnmounted, toRef } from 'vue'

const props = defineProps(parallelChartProps<EccentricBracedFrameField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

// query via inject (not prop) so a filter change doesn't re-render this chart.
const query = inject(dashboardQueryKey, toRef(props, 'query'))
const { getMatrix, matrixSync } = useDataset(EBF_KEY, fetchEbfs)
const { changeSearches, data, ids, requestFields, isFiltered } =
  useParallelChart<EccentricBracedFrameField>(
    emit,
    EccentricBracedFrameField.Id,
    props.fields,
    query,
    getMatrix
  )

// Live crossfilter during a drag: recompute the matrix from the in-memory dataset
// and feed the existing reactive data/ids refs (kept reactive — the per-frame cost
// is the N-polyline canvas redraw, identical either way, and this leaves the chart's
// brush-select untouched). The reactive commit refreshes these on pointer-up.
const unsubscribe = subscribeCrossfilter({
  onLive: (liveQuery) => {
    const model = matrixSync(requestFields.value, liveQuery)
    ids.value = model.ids
    data.value = model.data as unknown as (string | number)[][]
  },
  onSettle: () => {}
})
onUnmounted(unsubscribe)
</script>

<template>
  <simple-parallel-chart
    :animate="false"
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
