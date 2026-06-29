<script setup lang="ts">
/**
 * Date-range variant of {@link DistributionBrush}: maps date strings to day
 * numbers for the underlying numeric brush and formats the bounds back to dates.
 */
import DistributionBrush from '@/components/commons/sliders/DistributionBrush.vue'
import { mapDateToNumber, mapNumberToDate } from '@/utils/date'
import type { Color } from '@/utils/vuetify'
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    modelValue?: [string, string]
    min: string
    max: string
    // Distribution shape as [dayNumber, count] pairs (already numeric positions).
    distribution?: [number, number][]
    color?: Color
    type?: 'bar' | 'line'
  }>(),
  {
    modelValue: undefined,
    distribution: () => [],
    color: undefined,
    type: 'bar'
  }
)
const emit = defineEmits<{
  (e: 'update:modelValue', value: [string, string]): void
}>()

const minNumber = computed(() => mapDateToNumber(props.min))
const maxNumber = computed(() => mapDateToNumber(props.max))

const rangeNumber = computed<[number, number] | undefined>({
  get: () =>
    props.modelValue ? (props.modelValue.map(mapDateToNumber) as [number, number]) : undefined,
  set: (value) => {
    if (value) emit('update:modelValue', value.map(mapNumberToDate) as [string, string])
  }
})
</script>

<template>
  <distribution-brush
    :color="color"
    :distribution="distribution"
    :formatter="mapNumberToDate"
    :max="maxNumber"
    :min="minNumber"
    :model-value="rangeNumber"
    :step="1"
    :type="type"
    @update:model-value="rangeNumber = $event"
  />
</template>
