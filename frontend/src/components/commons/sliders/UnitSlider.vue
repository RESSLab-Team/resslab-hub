<script setup lang="ts">
import { useColor } from '@/composables/color'
import { useUnits } from '@/composables/unit'
import type { Color } from '@/utils/vuetify'
import { computed, withDefaults } from 'vue'

export interface UnitSliderItem<K = string> {
  key: K
  label: string
  min: number
  max: number
  unit?: string
}

export interface Variable<K extends string = string> {
  key: K
  text: string
  unit?: string
  min: number
  max: number
}

const props = withDefaults(
  defineProps<{
    modelValue: number
    color?: Color
    unit?: string
    disabled?: boolean
    label: string
    min: number
    max: number
  }>(),
  {
    color: undefined,
    unit: undefined,
    disabled: false
  }
)
const emit = defineEmits<{
  (e: 'update:modelValue', value: number): void
}>()

const precision = 100

const { baseColor, darkenColor, lightenColor } = useColor(props.color)
const { ratio, unitLabel } = useUnits(props.unit)

const sliderModel = computed<number>({
  get: () => props.modelValue / ratio.value,
  set: (value) => emit('update:modelValue', value * ratio.value)
})
const textModel = computed<string>({
  get: () => (Math.round(sliderModel.value * precision) / precision).toString(),
  set: (value) => (sliderModel.value = Number(value))
})
const displayedMin = computed<number>(() => props.min / ratio.value)
const displayedMax = computed<number>(() => props.max / ratio.value)
</script>

<template>
  <v-sheet class="pa-1" elevation="1" rounded>
    <v-slider
      v-model="sliderModel"
      :color="baseColor"
      density="compact"
      :disabled="disabled"
      hide-details
      :max="displayedMax"
      :min="displayedMin"
      step="0"
      :thumb-color="darkenColor"
      :track-color="lightenColor"
    >
      <template #prepend>
        <v-tooltip bottom>
          <!-- eslint-disable-next-line vue/no-template-shadow -->
          <template #activator="{ props }">
            <div class="mt-0 pt-0 label" v-bind="props">
              <!-- eslint-disable-next-line vue/no-v-html -->
              <span v-html="label" />
              <template v-if="unitLabel"> [{{ unitLabel }}]</template>
            </div>
          </template>
          <!-- eslint-disable-next-line vue/no-v-html -->
          <span v-html="label" />
          <template v-if="unitLabel"> [{{ unitLabel }}]</template>
        </v-tooltip>
      </template>
      <template #append>
        <v-text-field
          v-model="textModel"
          class="mt-0 pt-0"
          density="compact"
          hide-details
          :max="displayedMax"
          :min="displayedMin"
          single-line
          type="number"
          variant="underlined"
        />
      </template>
    </v-slider>
  </v-sheet>
</template>

<style lang="scss" scoped>
.v-input__slider {
  align-items: center;
}
div.label {
  line-height: initial;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.v-input__append,
.v-input__prepend {
  & > div {
    width: 84px;
  }
}
</style>
