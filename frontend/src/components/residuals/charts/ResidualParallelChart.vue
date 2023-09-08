<script setup lang="ts">
import { ResidualStressField } from '@/backend'
import SimpleParallelChart from '@/components/commons/charts/SimpleParallelChart.vue'
import { parallelChartProps, useParallelChart, type ChartEmits } from '@/composables/chart'
import { residualsApi } from '@/plugins/axios'
import { toRef } from 'vue'

const props = defineProps(parallelChartProps<ResidualStressField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

const { changeSearches, data, ids, requestFields, isFiltered } =
  useParallelChart<ResidualStressField>(
    emit,
    ResidualStressField.Id,
    props.fields,
    toRef(props, 'query'),
    (fields, query) => residualsApi.getResidualStressesMatrix(fields, query)
  )
</script>

<template>
  <simple-parallel-chart
    :color="color"
    :data="data"
    :fields="fields"
    :ids="ids"
    :is-filtered="isFiltered"
    label-prefix="residual."
    :request-fields="requestFields"
    @change:searches="changeSearches"
  />
</template>
