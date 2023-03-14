<script setup lang="ts">
import { useColor } from '@/composables/color'
import { mapDateToNumber, mapNumberToDate } from '@/utils/date'
import type { Color } from '@/utils/vuetify'
import { computed, withDefaults } from 'vue'

const props = withDefaults(
  defineProps<{
    modelValue?: [string, string]
    min: string
    max: string
    color?: Color
  }>(),
  {
    modelValue: undefined,
    value: undefined,
    color: undefined
  }
)
const emit = defineEmits<{
  (e: 'update:modelValue', value: [string, string]): void
}>()

const vTextBind = {
  class: 'mt-0 pt-0',
  density: 'compact' as 'compact',
  hideDetails: true,
  readonly: true,
  singleLine: true,
  style: 'width: 82px',
  variant: 'underlined' as 'underlined'
}

const { baseColor, darkenColor, lightenColor } = useColor(props.color)

const range = computed<[string, string]>({
  get: () => props.modelValue ?? [props.min, props.max],
  set: (value) => emit('update:modelValue', value)
})
const rangeNumber = computed<[number, number]>({
  get: () => range.value.map(mapDateToNumber) as [number, number],
  set: (value) => (range.value = value.map(mapNumberToDate) as [string, string])
})
const maxNumber = computed(() => mapDateToNumber(props.max))
const minNumber = computed(() => mapDateToNumber(props.min))
</script>

<template>
  <div>
    <v-range-slider
      v-model="rangeNumber"
      class="align-center"
      :color="baseColor"
      hide-details
      :min="minNumber"
      :max="maxNumber"
      :thumb-color="darkenColor"
      :track-color="lightenColor"
    >
      <template #prepend>
        <v-text-field v-bind="vTextBind" :model-value="range[0]" />
      </template>
      <template #append>
        <v-text-field v-bind="vTextBind" :model-value="range[1]" />
      </template>
    </v-range-slider>
  </div>
</template>
