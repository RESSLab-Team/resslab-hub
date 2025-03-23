<script setup lang="ts">
import { EccentricBracedFrameField, EccentricBracedFrameNumberField } from '@/backend'
import DoubleChart from '@/components/commons/charts/DoubleChart.vue'
import { doubleChartProps, useDoubleChart, type ChartEmits } from '@/composables/chart'
import { ebfApi } from '@/plugins/axios'
import { toRef } from 'vue'

const props = defineProps(doubleChartProps<EccentricBracedFrameField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

const { counts, changeSearches, dateMax, dateMin, dateRange, numberMax, numberMin, numberRange } =
  useDoubleChart<EccentricBracedFrameField, EccentricBracedFrameNumberField>(
    emit,
    props.fields,
    toRef(props, 'query'),
    (fields, query) => ebfApi.getEccentricBracedFramesCounts(fields, query),
    {
      field: EccentricBracedFrameNumberField,
      getRange: (field) => ebfApi.getEccentricBracedFramesRange(field)
    }
  )
</script>

<template>
  <double-chart
    v-model:date-range="dateRange"
    v-model:number-range="numberRange"
    :color="color"
    :counts="counts"
    :date-max="dateMax"
    :date-min="dateMin"
    :fields="fields"
    label-prefix="ebf."
    :number-max="numberMax"
    :number-min="numberMin"
    :type="props.type"
    @change:searches="changeSearches"
  />
</template>
