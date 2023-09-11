<script setup lang="ts">
import type { Value } from '@/utils/common'

const props = defineProps<{
  field: string
  isFiltered: boolean
}>()

const emit = defineEmits<{
  (e: 'change:searches', key: string, value?: Value): void
}>()

function resetFilters(): void {
  emit('change:searches', props.field, undefined)
}
</script>

<template>
  <v-btn color="primary" :disabled="!isFiltered" variant="text" @click="resetFilters">
    Reset
  </v-btn>
</template>

<style scoped>
/* .v-btn {
  padding: 0.5rem;
  min-height: 52px;
  margin-bottom: -18px;
  margin-left: -0.5rem;
} */
</style>
