<script setup lang="ts">
import type { ResidualStressField } from '@/backend'
import SingleChart from '@/components/commons/charts/SingleChart.vue'
import { singleChartProps, useSingleChart, type ChartEmits } from '@/composables/chart'
import { dashboardQueryKey } from '@/composables/dashboard'
import { useDataset } from '@/composables/useDataset'
import { RESIDUAL_KEY, fetchResiduals } from '@/components/residuals/data'
import { inject, toRef } from 'vue'

const props = defineProps(singleChartProps<ResidualStressField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

// query via inject (not prop) so a filter change doesn't re-render this chart —
// it updates only when its own counts change. See dashboardQueryKey.
const query = inject(dashboardQueryKey, toRef(props, 'query'))
const { getCounts, countsSync } = useDataset(RESIDUAL_KEY, fetchResiduals)
const { counts, changeSearches } = useSingleChart<ResidualStressField>(
  emit,
  props.field,
  query,
  getCounts
)

// Synchronous counts for the crossfilter drag path — mapped/sorted to match the
// composable's reactive `counts` so live frames are pixel-identical.
const getLiveCounts = (liveQuery?: string) =>
  countsSync([props.field], liveQuery)
    .map((count) => ({ name: count.names[0], value: count.value }))
    .sort((a, b) => (a.name < b.name ? -1 : 1))
</script>

<template>
  <single-chart
    :animate="false"
    :color="color"
    :counts="counts"
    :live-counts="getLiveCounts"
    :show-reset="showReset"
    :flat="flat"
    :field="field"
    label-prefix="residual."
    @change:searches="changeSearches"
  >
    <template #title><slot name="title"></slot></template>
  </single-chart>
</template>
