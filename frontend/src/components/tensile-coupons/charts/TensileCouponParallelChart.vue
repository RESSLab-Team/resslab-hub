<script setup lang="ts">
import { TensileCouponField } from '@/backend'
import SimpleParallelChart from '@/components/commons/charts/SimpleParallelChart.vue'
import { parallelChartProps, useParallelChart, type ChartEmits } from '@/composables/chart'
import { tensileCouponApi } from '@/plugins/axios'
import { toRef } from 'vue'

const props = defineProps(parallelChartProps<TensileCouponField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

const { changeSearches, data, ids, requestFields, isFiltered } = useParallelChart<TensileCouponField>(
  emit,
  TensileCouponField.Id,
  props.fields,
  toRef(props, 'query'),
  (fields, query) => tensileCouponApi.getTensileCouponsMatrix(fields, query)
)
</script>

<template>
  <simple-parallel-chart
    :color="color"
    :data="data"
    :fields="fields"
    :ids="ids"
    :is-filtered="isFiltered"
    label-prefix="tensile_coupon."
    :request-fields="requestFields"
    @change:searches="changeSearches"
  />
</template>
