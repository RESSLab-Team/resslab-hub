<script setup lang="ts">
import type { BraceField } from '@/backend'
import SingleChart from '@/components/commons/charts/SingleChart.vue'
import { singleChartProps, useSingleChart, type ChartEmits } from '@/composables/chart'
import { bracesApi } from '@/plugins/axios'
import { toRef } from 'vue'

const props = defineProps(singleChartProps<BraceField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

const { counts, changeSearches } = useSingleChart<BraceField>(
  emit,
  props.field,
  toRef(props, 'query'),
  (fields, query) => bracesApi.getBracesCounts(fields, query)
)
</script>

<template>
  <single-chart
    :color="color"
    :counts="counts"
    :field="field"
    label-prefix="brace."
    @change:searches="changeSearches"
  >
    <template #title> <slot name="title" /> </template>
  </single-chart>
</template>
