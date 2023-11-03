<script setup lang="ts">
import type { HSSColumnField } from '@/backend'
import SingleChart from '@/components/commons/charts/SingleChart.vue'
import { singleChartProps, useSingleChart, type ChartEmits } from '@/composables/chart'
import { hssApi } from '@/plugins/axios'
import { toRef } from 'vue'

const props = defineProps(singleChartProps<HSSColumnField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

const { counts, changeSearches } = useSingleChart<HSSColumnField>(
  emit,
  props.field,
  toRef(props, 'query'),
  (fields, query) => hssApi.getHssColumnsCounts(fields, query)
)
</script>

<template>
  <single-chart
    :color="color"
    :counts="counts"
    :flat="flat"
    :field="field"
    :show-reset="showReset"
    label-prefix="hss."
    @change:searches="changeSearches"
  >
    <template #title> <slot name="title" /> </template>
  </single-chart>
</template>
