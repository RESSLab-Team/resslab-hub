<script setup lang="ts">
import type { MaterialField, MaterialModel } from '@/backend'
import SingleChart from '@/components/commons/charts/SingleChart.vue'
import { singleChartProps, useSingleChart, type ChartEmits } from '@/composables/chart'
import { dashboardQueryKey } from '@/composables/dashboard'
import { useDataset } from '@/composables/useDataset'
import { MATERIAL_KEY, fetchMaterials } from '@/components/materials/data'
import { inject, toRef } from 'vue'

const props = defineProps(singleChartProps<MaterialField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

// query via inject (not prop) so a filter change doesn't re-render this chart —
// it updates only when its own counts change. See dashboardQueryKey.
const query = inject(dashboardQueryKey, toRef(props, 'query'))
const { getCounts, countsSync } = useDataset<MaterialModel>(MATERIAL_KEY, fetchMaterials)
const { counts, changeSearches } = useSingleChart<MaterialField>(emit, props.field, query, getCounts)

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
    label-prefix="material."
    @change:searches="changeSearches"
  >
    <template #title><slot name="title"></slot></template>
  </single-chart>
</template>
