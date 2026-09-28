<script setup lang="ts">
import type { Value } from '@/utils/common'
import type { DoubleFields } from '@/composables/chart'

const props = defineProps<{
  field: string | DoubleFields | string[]

  isFiltered: boolean
}>()

const emit = defineEmits<{
  (e: 'change:searches', key: string, value?: Value): void
}>()

function resetFilters(): void {
  if (typeof props.field === 'string') emit('change:searches', props.field, undefined)
  else if (Array.isArray(props.field))
    for (const key of props.field as string[]) emit('change:searches', key, undefined)
  else {
    emit('change:searches', props.field[0], undefined)
    if (typeof props.field[1] === 'string') emit('change:searches', props.field[1], undefined)
  }
}
</script>

<template>
  <v-btn color="primary" :disabled="!isFiltered" variant="text" @click="resetFilters">
    {{ $t('commons.reset') }}
  </v-btn>
</template>
