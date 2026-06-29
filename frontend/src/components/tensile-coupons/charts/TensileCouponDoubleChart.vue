<script setup lang="ts">
import { TensileCouponField, TensileCouponNumberField } from '@/backend'
import DoubleChart from '@/components/commons/charts/DoubleChart.vue'
import { doubleChartProps, useDoubleChart, type ChartEmits } from '@/composables/chart'
import { tensileCouponApi } from '@/plugins/axios'
import { toRef } from 'vue'

const props = defineProps(doubleChartProps<TensileCouponField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

const {
  counts,
  allCounts,
  changeSearches,
  dateMax,
  dateMin,
  dateRange,
  numberMax,
  numberMin,
  numberRange
} = useDoubleChart<TensileCouponField, TensileCouponNumberField>(
  emit,
  props.fields,
  toRef(props, 'query'),
  (fields, query) => tensileCouponApi.getTensileCouponsCounts(fields, query),
  {
    field: TensileCouponNumberField,
    getRange: (field) => tensileCouponApi.getTensileCouponsRange(field)
  }
)
</script>

<template>
  <double-chart
    v-model:date-range="dateRange"
    v-model:number-range="numberRange"
    :all-counts="allCounts"
    :color="color"
    :counts="counts"
    :date-max="dateMax"
    :date-min="dateMin"
    :fields="fields"
    label-prefix="tensile_coupon."
    :number-max="numberMax"
    :number-min="numberMin"
    :type="props.type"
    @change:searches="changeSearches"
  />
</template>
