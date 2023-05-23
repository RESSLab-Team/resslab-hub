<script setup lang="ts">
import type { ToggleItem } from '@/utils/toggle'
import { computed } from 'vue'

// TODO add genericity https://github.com/vuejs/rfcs/discussions/436
type T = string
const props = withDefaults(
  defineProps<{
    modelValue: T
    items?: ToggleItem<T>[]
  }>(),
  {
    items: () => []
  }
)
const emit = defineEmits<{
  (e: 'update:modelValue', value: T): void
}>()

const index = computed<number>({
  get: () => props.items.findIndex((item) => item.value === props.modelValue) ?? 0,
  set: (value) => emit('update:modelValue', props.items[value].value)
})
</script>

<template>
  <v-btn-toggle v-model="index" density="compact" mandatory variant="outlined">
    <v-btn v-for="item in items" :key="item.value">{{ item.text }}</v-btn>
  </v-btn-toggle>
</template>
