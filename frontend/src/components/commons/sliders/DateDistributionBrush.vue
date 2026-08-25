<script setup lang="ts">
/**
 * Date-range variant of {@link DistributionBrush}: maps date strings to day
 * numbers for the underlying numeric brush and formats the bounds back to dates.
 */
import DistributionBrush, {
  type BrushSeries
} from '@/components/commons/sliders/DistributionBrush.vue'
import { mapDateToNumber, mapNumberToDate } from '@/utils/date'
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    modelValue?: [string, string]
    min: string
    max: string
    // Stacked series with [dayNumber, count] points (already numeric positions).
    series?: BrushSeries[]
    type?: 'bar' | 'line'
    fields?: 'sides' | 'below'
  }>(),
  {
    modelValue: undefined,
    series: () => [],
    type: 'bar',
    fields: 'sides'
  }
)
const emit = defineEmits<{
  (e: 'update:modelValue', value: [string, string]): void
  (e: 'dragend'): void
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
    :fields="fields"
    :formatter="mapNumberToDate"
    :max="maxNumber"
    :min="minNumber"
    :model-value="rangeNumber"
    :series="series"
    :step="1"
    :type="type"
    @dragend="$emit('dragend')"
    @update:model-value="rangeNumber = $event"
  />
</template>
