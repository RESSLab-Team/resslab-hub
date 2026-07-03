<script setup lang="ts">
import type { ColumnField } from '@/backend'
import SingleChart from '@/components/commons/charts/SingleChart.vue'
import { singleChartProps, toSingleCounts, useSingleChart, type ChartEmits } from '@/composables/chart'
import { dashboardQueryKey } from '@/composables/dashboard'
import { useDataset } from '@/composables/useDataset'
import { COLUMN_KEY, fetchColumns } from '@/components/columns/data'
import { inject, toRef } from 'vue'

const props = defineProps(singleChartProps<ColumnField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

// query via inject (not prop) so a filter change doesn't re-render this chart —
// it updates only when its own counts change. See dashboardQueryKey.
const query = inject(dashboardQueryKey, toRef(props, 'query'))
const { getCounts, countsSync } = useDataset(COLUMN_KEY, fetchColumns)
const { counts, changeSearches } = useSingleChart<ColumnField>(emit, props.field, query, getCounts)

// Synchronous counts for the crossfilter drag path — same mapping as the
// composable's reactive `counts`, so live frames are pixel-identical.
const getLiveCounts = (liveQuery?: string) => toSingleCounts(countsSync([props.field], liveQuery))
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
    label-prefix="column."
    @change:searches="changeSearches"
  >
    <template #title><slot name="title"></slot></template>
  </single-chart>
</template>
