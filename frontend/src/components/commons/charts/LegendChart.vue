<script setup lang="ts">
import { computed } from 'vue'

export interface LegendItem {
  selected: boolean
  label: string
  color: string
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
      :on-icon="item.icon"
      :off-icon="item.icon"
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

// Transform rectangles into "lines" symbols
:deep(.legend-checkbox) .mdi-rectangle {
  transform: scale(1.3, 0.4);
}
</style>
