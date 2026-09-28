<script setup lang="ts">
import { ConnectionField } from '@/backend'
import SingleChart from '@/components/commons/charts/SingleChart.vue'
import {
  singleChartProps,
  toSingleCounts,
  useSingleChart,
  type ChartEmits
} from '@/composables/chart'
import { dashboardQueryKey } from '@/composables/dashboard'
import { useDataset } from '@/composables/useDataset'
import { CONNECTION_KEY, fetchConnections } from '@/components/connections/data'
import { getConnectionTypeImage } from '@/utils/component'
import { inject, toRef } from 'vue'

const props = defineProps(singleChartProps<ConnectionField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

// query via inject (not prop) so a filter change doesn't re-render this chart —
// it updates only when its own counts change. See dashboardQueryKey.
const query = inject(dashboardQueryKey, toRef(props, 'query'))
const { getCounts, countsSync, colorFor } = useDataset(CONNECTION_KEY, fetchConnections)
// Stable reference: a fresh closure per render would re-render the chart for nothing.
const colorForField = colorFor(props.field)
const { counts, changeSearches } = useSingleChart<ConnectionField>(
  emit,
  props.field,
  query,
  getCounts
)

// Synchronous counts for the crossfilter drag path — same mapping as the
// composable's reactive `counts`, so live frames are pixel-identical.
const getLiveCounts = (liveQuery?: string) => toSingleCounts(countsSync([props.field], liveQuery))

const imageFor = props.field === ConnectionField.ConnectionType ? getConnectionTypeImage : undefined
</script>

<template>
  <single-chart
    :animate="false"
    :color-for="colorForField"
    :counts="counts"
    :live-counts="getLiveCounts"
    :flat="flat"
    :show-reset="showReset"
    :field="field"
    :image-for="imageFor"
    label-prefix="connection."
    @change:searches="changeSearches"
  >
    <template #title> <slot name="title"></slot> </template>
  </single-chart>
</template>
