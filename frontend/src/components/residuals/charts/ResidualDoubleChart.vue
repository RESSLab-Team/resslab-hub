<script setup lang="ts">
import { ResidualStressNumberField, type ResidualStressField } from '@/backend'
import DoubleChart from '@/components/commons/charts/DoubleChart.vue'
import { doubleChartProps, useDoubleChart, type ChartEmits } from '@/composables/chart'
import { residualsApi } from '@/plugins/axios'
import { computed, toRef } from 'vue'

const props = defineProps({
  ...doubleChartProps<ResidualStressField>(),
  bin: { type: Number, required: false, default: null }
})
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

const { counts, changeSearches, dateMax, dateMin, dateRange, numberMax, numberMin, numberRange } =
  useDoubleChart<ResidualStressField, ResidualStressNumberField>(
    emit,
    props.fields,
    toRef(props, 'query'),
    (fields, query) => residualsApi.getResidualStressesCounts(fields, query),
    {
      field: ResidualStressNumberField,
      getRange: (field) => residualsApi.getResidualStressesRange(field)
    }
  )

const binnedCounts = computed(() => {
  if (props.bin === null) {
    return counts.value
  }
  const bins = new Map<[string, string], number>()

  for (const count of counts.value) {
    // Calculate the bin that this count belongs to

    const bin = Math.floor(Number(count.names[0]) / 100) * 100,
      type = count.names[1]
    console.log('Count', count, bin)

    // Get the current count for this bin, defaulting to 0 if it doesn't exist
    const currentCount = bins.get([bin.toString(), type]) || 0

    // Add this count to the bin
    bins.set([bin.toString(), type], currentCount + count.value)
  }

  return Array.from(bins.entries()).map(([names, count]) => ({ names, value: count }))
})
</script>

<template>
  <double-chart
    v-model:date-range="dateRange"
    v-model:number-range="numberRange"
    :color="color"
    :counts="binnedCounts"
    :date-max="dateMax"
    :date-min="dateMin"
    :fields="fields"
    label-prefix="residual."
    :number-max="numberMax"
    :number-min="numberMin"
    :type="props.type"
    @change:searches="changeSearches"
  />
</template>
