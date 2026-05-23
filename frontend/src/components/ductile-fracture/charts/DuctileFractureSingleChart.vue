<script setup lang="ts">
import type { DuctileFractureField } from '@/backend'
import SingleChart from '@/components/commons/charts/SingleChart.vue'
import { singleChartProps, useSingleChart, type ChartEmits } from '@/composables/chart'
import { ductileFractureApi } from '@/plugins/axios'
import { toRef } from 'vue'

const props = defineProps(singleChartProps<DuctileFractureField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

const { counts, changeSearches } = useSingleChart<DuctileFractureField>(
  emit,
  props.field,
  toRef(props, 'query'),
  (fields, query) => ductileFractureApi.getDuctileFracturesCounts(fields, query)
)
</script>

<template>
  <single-chart
    :color="color"
    :counts="counts"
    :flat="flat"
    :show-reset="showReset"
    :field="field"
    label-prefix="ductile_fracture."
    @change:searches="changeSearches"
  >
    <template #title><slot name="title"></slot></template>
  </single-chart>
</template>
