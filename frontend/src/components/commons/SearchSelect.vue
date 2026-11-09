<script setup lang="ts" generic="V extends string | number | object">
import type { SelectItem } from '@/utils/vuetify'
import { mdiMagnify } from '@mdi/js'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = withDefaults(
  defineProps<{
    modelValue?: V
    items?: SelectItem<V>[]
    label?: string
  }>(),
  {
    modelValue: undefined,
    items: () => [],
    label: undefined
  }
)
const emit = defineEmits<{
  (e: 'update:modelValue', value?: V): void
}>()

const { t } = useI18n({ useScope: 'global' })

const value = computed<V | undefined>({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value ?? undefined)
})
</script>

<template>
  <!-- Type-to-filter select: shows every item when empty, narrows as you type. -->
  <v-autocomplete
    v-model="value"
    autocomplete="off"
    clearable
    hide-details
    :items="items"
    :label="label"
    :menu-props="{ maxHeight: 340 }"
    :no-data-text="t('commons.no_results')"
    :prepend-inner-icon="mdiMagnify"
    variant="outlined"
  />
</template>
