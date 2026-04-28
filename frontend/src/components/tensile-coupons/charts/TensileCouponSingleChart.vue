<script setup lang="ts">
import type { TensileCouponField } from '@/backend'
import SingleChart from '@/components/commons/charts/SingleChart.vue'
import { singleChartProps, useSingleChart, type ChartEmits } from '@/composables/chart'
import { tensileCouponApi } from '@/plugins/axios'
import { toRef } from 'vue'

const props = defineProps(singleChartProps<TensileCouponField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

const { counts, changeSearches } = useSingleChart<TensileCouponField>(
  emit,
  props.field,
  toRef(props, 'query'),
  (fields, query) => tensileCouponApi.getTensileCouponsCounts(fields, query)
)
</script>

<template>
  <single-chart
    :color="color"
    :counts="counts"
    :flat="flat"
    :field="field"
    label-prefix="tensile_coupon."
    @change:searches="changeSearches"
  >
    <template #title><slot name="title"></slot></template>
  </single-chart>
</template>
