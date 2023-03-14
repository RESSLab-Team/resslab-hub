<script setup lang="ts">
import { useColor } from '@/composables/color'
import type { Color } from '@/utils/vuetify'
import { computed, withDefaults } from 'vue'

const props = withDefaults(
  defineProps<{
    modelValue?: [number, number]
    min: number
    max: number
    step?: number
    color?: Color
  }>(),
  {
    modelValue: undefined,
    step: 1,
    color: undefined
  }
)
const emit = defineEmits<{
  (e: 'update:modelValue', value: [number, number]): void
}>()

const { baseColor, darkenColor, lightenColor } = useColor(props.color)

const actualMin = computed<number>(() => props.min - (props.min % props.step))
const actualMax = computed<number>(() => Math.ceil(props.max / props.step) * props.step)
const range = computed<[number, number]>({
  get: () => props.modelValue ?? [actualMin.value, actualMax.value],
  set: (value) =>
    emit('update:modelValue', [
      Math.max(actualMin.value, value[0]),
      Math.min(actualMax.value, value[1])
    ])
})
const vTextBind = computed(() => ({
  class: 'mt-0 pt-0',
  density: 'compact' as 'compact',
  hideDetails: true,
  min: actualMin.value,
  max: actualMax.value,
  singleLine: true,
  style: 'width: 60px',
  type: 'number',
  variant: 'underlined' as 'underlined'
}))

function onMinChanged(min: string): void {
  range.value = [Number(min), range.value[1]]
}

function onMaxChanged(max: string): void {
  range.value = [range.value[0], Number(max)]
}
</script>

<template>
  <v-range-slider
    v-model="range"
    class="align-center"
    :color="baseColor"
    hide-details
    :min="actualMin"
    :max="actualMax"
    :step="step"
    :thumb-color="darkenColor"
    :track-color="lightenColor"
  >
    <template #prepend>
      <v-text-field v-bind="vTextBind" :model-value="range[0]" @change="onMinChanged" />
    </template>
    <template #append>
      <v-text-field v-bind="vTextBind" :model-value="range[1]" @change="onMaxChanged" />
    </template>
  </v-range-slider>
</template>
