<script setup lang="ts">
import type { EccentricBracedFrameField } from '@/backend'
import SingleChart from '@/components/commons/charts/SingleChart.vue'
import { singleChartProps, useSingleChart, type ChartEmits } from '@/composables/chart'
import { dashboardQueryKey } from '@/composables/dashboard'
import { useDataset } from '@/composables/useDataset'
import { EBF_KEY, fetchEbfs } from '@/components/ebf/data'
import { toRef, computed, inject } from 'vue'
import { linkConfigurationMapping } from '@/utils/ebf'

const props = defineProps(singleChartProps<EccentricBracedFrameField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

// Create a mapping based on the field type
const valueMapping = computed(() => {
  if (props.field === 'l_confi') {
    return linkConfigurationMapping
  }
  return undefined
})

// query via inject (not prop) so a filter change doesn't re-render this chart —
// it updates only when its own counts change. See dashboardQueryKey.
const query = inject(dashboardQueryKey, toRef(props, 'query'))
const { getCounts, countsSync } = useDataset(EBF_KEY, fetchEbfs)
const { counts, changeSearches } = useSingleChart<EccentricBracedFrameField>(
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
    :flat="flat"
    :field="field"
    :show-reset="showReset"
    :mapping="valueMapping"
    label-prefix="ebf."
    @change:searches="changeSearches"
  >
    <template #title>
      <slot name="title" />
    </template>
  </single-chart>
</template>
