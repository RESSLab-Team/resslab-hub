<script setup lang="ts">
import type { ResidualStressField } from '@/backend'
import SingleChart from '@/components/commons/charts/SingleChart.vue'
import { singleChartProps, useSingleChart, type ChartEmits } from '@/composables/chart'
import { residualsApi } from '@/plugins/axios'
import { toRef } from 'vue'

const props = defineProps(singleChartProps<ResidualStressField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

const { counts, changeSearches } = useSingleChart<ResidualStressField>(
  emit,
  props.field,
  toRef(props, 'query'),
  (fields, query) => residualsApi.getResidualStressesCounts(fields, query)
)
</script>

<template>
  <single-chart
    :color="color"
    :counts="counts"
    :show-reset="showReset"
    :flat="flat"
    :field="field"
    label-prefix="residual."
    @change:searches="changeSearches"
  >
    <template #title><slot name="title"></slot></template>
  </single-chart>
</template>
