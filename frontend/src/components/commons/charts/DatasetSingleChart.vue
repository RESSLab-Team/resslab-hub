<script setup lang="ts" generic="F extends string">
// A dashboard treemap bound to its dataset: counts come from the in-browser
// dataset (useDataset), colors stay stable per value. `source` says which
// dataset, from `components/{type}/data.ts`.
import SingleChart from '@/components/commons/charts/SingleChart.vue'
import {
  toSingleCounts,
  useSingleChart,
  type ChartEmits,
  type DatasetSource
} from '@/composables/chart'
import { dashboardQueryKey } from '@/composables/dashboard'
import { useDataset } from '@/composables/useDataset'
import { inject, toRef } from 'vue'

const props = defineProps<{
  source: DatasetSource<F>
  field: NoInfer<F>
  query?: string
  showReset?: boolean
  flat?: boolean
  // Raw value → display label, for fields stored as codes.
  mapping?: Map<string, string>
  // Figure shown in the tooltip of a hovered value (see SingleChart).
  imageFor?: (value: string) => string | undefined
}>()
const emit = defineEmits<ChartEmits>()

// query via inject (not prop) so a filter change doesn't re-render this chart:
// it updates only when its own counts change. See dashboardQueryKey.
const query = inject(
  dashboardQueryKey,
  toRef(() => props.query)
)
const { getCounts, countsSync, colorFor } = useDataset(props.source.key, props.source.fetchAll)
// Stable reference: a fresh closure per render would re-render the chart for nothing.
const colorForField = colorFor(props.field)
const { counts, changeSearches } = useSingleChart<F>(emit, props.field, query, getCounts)

// Synchronous counts for the crossfilter drag path: same mapping as the
// composable's reactive `counts`, so live frames are pixel-identical.
const getLiveCounts = (liveQuery?: string) => toSingleCounts(countsSync([props.field], liveQuery))
</script>

<template>
  <single-chart
    :animate="false"
    :color-for="colorForField"
    :counts="counts"
    :live-counts="getLiveCounts"
    :flat="flat"
    :field="field"
    :image-for="imageFor"
    :label-prefix="source.labelPrefix"
    :mapping="mapping"
    :show-reset="showReset"
    @change:searches="changeSearches"
  />
</template>
