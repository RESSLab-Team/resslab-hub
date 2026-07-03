<script setup lang="ts">
import { ConnectionField } from '@/backend'
import SingleChart from '@/components/commons/charts/SingleChart.vue'
import { singleChartProps, toSingleCounts, useSingleChart, type ChartEmits } from '@/composables/chart'
import { dashboardQueryKey } from '@/composables/dashboard'
import { useDataset } from '@/composables/useDataset'
import { CONNECTION_KEY, fetchConnections } from '@/components/connections/data'
import { publicPath } from '@/utils/common'
import type { CallbackDataParams } from 'echarts/types/dist/shared'
import { inject, ref, toRef } from 'vue'

const props = defineProps(singleChartProps<ConnectionField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

// query via inject (not prop) so a filter change doesn't re-render this chart —
// it updates only when its own counts change. See dashboardQueryKey.
const query = inject(dashboardQueryKey, toRef(props, 'query'))
const { getCounts, countsSync } = useDataset(CONNECTION_KEY, fetchConnections)
const { counts, changeSearches } = useSingleChart<ConnectionField>(emit, props.field, query, getCounts)

// Synchronous counts for the crossfilter drag path — same mapping as the
// composable's reactive `counts`, so live frames are pixel-identical.
const getLiveCounts = (liveQuery?: string) => toSingleCounts(countsSync([props.field], liveQuery))

const imageUrl = ref<string>()

function mouseover(params: CallbackDataParams): void {
  if (props.field === ConnectionField.ConnectionType) {
    const name: string = params.name.toLowerCase()
    imageUrl.value = publicPath + 'img/connection-type/' + name + '.svg'
  }
}

function mouseout(): void {
  imageUrl.value = undefined
}
</script>

<template>
  <single-chart
    :animate="false"
    :color="color"
    :counts="counts"
    :live-counts="getLiveCounts"
    :flat="flat"
    :show-reset="showReset"
    :field="field"
    label-prefix="connection."
    @change:searches="changeSearches"
    @mouseover="mouseover"
    @mouseout="mouseout"
  >
    <template #default>
      <v-img v-if="imageUrl" aspect-ratio="3" :src="imageUrl" min-height="120" />
    </template>
    <template #title> <slot name="title"></slot> </template>
  </single-chart>
</template>
