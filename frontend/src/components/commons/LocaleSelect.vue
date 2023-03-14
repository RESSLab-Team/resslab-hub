<script setup lang="ts">
import type { SelectItem } from '@/utils/vuetify'
import { computed, withDefaults } from 'vue'

const props = withDefaults(
  defineProps<{
    modelValue?: string
    items?: SelectItem[]
    prefix?: string
  }>(),
  {
    modelValue: '',
    items: () => [],
    prefix: ''
  }
)
const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const item = computed<string>({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})
</script>

<template>
  <v-select v-model="item" :items="items" hide-details>
    <template #selection="data">
      {{ $t(prefix + data.item) }}
    </template>
    <template #item="data">
      {{ $t(prefix + data.item) }}
    </template>
  </v-select>
</template>
