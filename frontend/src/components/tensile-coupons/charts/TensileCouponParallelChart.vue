<script setup lang="ts">
import { TensileCouponField } from '@/backend'
import SimpleParallelChart from '@/components/commons/charts/SimpleParallelChart.vue'
import { parallelChartProps, useParallelChart, type ChartEmits } from '@/composables/chart'
import { dashboardQueryKey } from '@/composables/dashboard'
import { useDataset } from '@/composables/useDataset'
import { TENSILE_COUPON_KEY, fetchTensileCoupons } from '@/components/tensile-coupons/data'
import { inject, toRef } from 'vue'

const props = defineProps(parallelChartProps<TensileCouponField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

// query via inject (not prop) so a filter change doesn't re-render this chart.
const query = inject(dashboardQueryKey, toRef(props, 'query'))
const { getMatrix, matrixSync } = useDataset(TENSILE_COUPON_KEY, fetchTensileCoupons)
const {
  changeSearches,
  commitSelection,
  data,
  highlightIds,
  ids,
  publishSelection,
  requestFields,
  isFiltered,
  zoomed
} = useParallelChart<TensileCouponField>(
  emit,
  TensileCouponField.Id,
  props.fields,
  query,
  getMatrix,
  matrixSync // live crossfilter drag frames (see useParallelChart)
)
</script>

<template>
  <simple-parallel-chart
    v-model:zoomed="zoomed"
    :animate="false"
    :highlight-ids="highlightIds"
    :data="data"
    :fields="fields"
    :ids="ids"
    :is-filtered="isFiltered"
    label-prefix="tensile_coupon."
    :request-fields="requestFields"
    @brush:commit="commitSelection"
    @brush:live="publishSelection"
    @change:searches="changeSearches"
  />
</template>
