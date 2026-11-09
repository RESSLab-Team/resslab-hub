<script lang="ts">
// Line samples for the legend swatches, as SVG path data. The app uses the
// mdi-svg icon set, so a checkbox icon is drawn as `<path d="...">` in a
// 24x24 box: a class name like `mdi-rectangle` would draw nothing.
/** A solid 2 px line, like a series with the default line style. */
export const LINE_SOLID = 'M2 11h20v2H2z'
/** A dotted 2 px line (2 px on, 2 px off), like ECharts' `dotted` at width 2. */
export const LINE_DOTTED = 'M3 11h2v2H3z M7 11h2v2H7z M11 11h2v2h-2z M15 11h2v2h-2z M19 11h2v2h-2z'
</script>

<script setup lang="ts">
import { computed } from 'vue'

export interface LegendItem {
  selected: boolean
  label: string
  color: string
  /** SVG path data, e.g. LINE_SOLID or LINE_DOTTED. */
  icon: string
}
function getClass(index: number): string {
  return `legend-checkbox ${props.separatorsIndex.includes(index) ? 'mt-4' : 'mt-0'}`
}

const props = withDefaults(
  defineProps<{
    modelValue?: LegendItem[]
    separatorsIndex?: number[]
  }>(),
  {
    modelValue: () => [],
    separatorsIndex: () => []
  }
)
const emit = defineEmits(['update:modelValue'])

const items = computed({
  get() {
    return props.modelValue
  },
  set(items) {
    emit('update:modelValue', items)
  }
})
</script>

<template>
  <div>
    <v-checkbox
      v-for="(item, index) in items"
      :key="index"
      v-model="item.selected"
      :hide-details="true"
      :ripple="false"
      :true-icon="item.icon"
      :false-icon="item.icon"
      :label="item.label"
      :color="item.color"
      :class="getClass(index)"
    />
  </div>
</template>

<style lang="scss" scoped>
:deep(.legend-checkbox) .v-icon {
  transition: none;
}
</style>
