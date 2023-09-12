<script setup lang="ts">
import type { ColumnField } from '@/backend'
import SingleChart from '@/components/commons/charts/SingleChart.vue'
import { singleChartProps, useSingleChart, type ChartEmits } from '@/composables/chart'
import { columnsApi } from '@/plugins/axios'
import { toRef } from 'vue'

const props = defineProps(singleChartProps<ColumnField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

const { counts, changeSearches } = useSingleChart<ColumnField>(
  emit,
  props.field,
  toRef(props, 'query'),
  (fields, query) => columnsApi.getColumnsCounts(fields, query)
)
</script>

<template>
  <single-chart
    :color="color"
    :counts="counts"
    :flat="flat"
    :field="field"
    label-prefix="column."
    @change:searches="changeSearches"
  >
    <template #title><slot name="title"></slot></template>
  </single-chart>
</template>
