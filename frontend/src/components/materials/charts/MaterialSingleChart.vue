<script setup lang="ts">
import type { MaterialField, MaterialModel } from '@/backend'
import SingleChart from '@/components/commons/charts/SingleChart.vue'
import {
  singleChartProps,
  toSingleCounts,
  useSingleChart,
  type ChartEmits
} from '@/composables/chart'
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
const { getCounts, countsSync, colorFor } = useDataset<MaterialModel>(MATERIAL_KEY, fetchMaterials)
const { counts, changeSearches } = useSingleChart<MaterialField>(
  emit,
  props.field,
  query,
  getCounts
)

// Synchronous counts for the crossfilter drag path — same mapping as the
// composable's reactive `counts`, so live frames are pixel-identical.
const getLiveCounts = (liveQuery?: string) => toSingleCounts(countsSync([props.field], liveQuery))
</script>

<template>
  <single-chart
    :animate="false"
    :color-for="colorFor(field)"
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
