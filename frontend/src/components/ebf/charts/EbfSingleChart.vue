<script setup lang="ts">
import type { EccentricBracedFrameField } from '@/backend'
import SingleChart from '@/components/commons/charts/SingleChart.vue'
import { singleChartProps, useSingleChart, type ChartEmits } from '@/composables/chart'
import { ebfApi } from '@/plugins/axios'
import { toRef, computed } from 'vue'
import { linkConfigurationMapping } from '@/utils/ebf'

const props = defineProps(singleChartProps<EccentricBracedFrameField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

// Create a mapping based on the field type
const valueMapping = computed(() => {
  if (props.field === 'l_confi') {
    return linkConfigurationMapping
  }
  return undefined
})

const { counts, changeSearches } = useSingleChart<EccentricBracedFrameField>(
  emit,
  props.field,
  toRef(props, 'query'),
  (fields, query) => ebfApi.getEccentricBracedFramesCounts(fields, query)
)
</script>

<template>
  <single-chart
    :color="color"
    :counts="counts"
    :flat="flat"
    :field="field"
    :show-reset="showReset"
    :mapping="valueMapping"
    label-prefix="ebf."
    @change:searches="changeSearches"
  >
    <template #title>
      <slot name="title" />
    </template>
  </single-chart>
</template>
