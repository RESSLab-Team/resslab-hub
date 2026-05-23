<script setup lang="ts">
import { DuctileFractureField, DuctileFractureNumberField } from '@/backend'
import DoubleChart from '@/components/commons/charts/DoubleChart.vue'
import { doubleChartProps, useDoubleChart, type ChartEmits } from '@/composables/chart'
import { ductileFractureApi } from '@/plugins/axios'
import { toRef } from 'vue'

const props = defineProps(doubleChartProps<DuctileFractureField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

const { counts, changeSearches, dateMax, dateMin, dateRange, numberMax, numberMin, numberRange } =
  useDoubleChart<DuctileFractureField, DuctileFractureNumberField>(
    emit,
    props.fields,
    toRef(props, 'query'),
    (fields, query) => ductileFractureApi.getDuctileFracturesCounts(fields, query),
    {
      field: DuctileFractureNumberField,
      getRange: (field) => ductileFractureApi.getDuctileFracturesRange(field)
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
    label-prefix="ductile_fracture."
    :number-max="numberMax"
    :number-min="numberMin"
    :type="props.type"
    @change:searches="changeSearches"
  />
</template>
