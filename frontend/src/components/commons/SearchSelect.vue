<script setup lang="ts">
import type { SelectItem } from '@/utils/vuetify'
import { mdiMagnify } from '@mdi/js'
import { computed, ref, unref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

// TODO add genericity https://github.com/vuejs/rfcs/discussions/436
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type V = string | number | object
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
const search = ref<string>()

const value = computed<V | undefined>({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})
const actualItems = computed<SelectItem[]>(() => {
  const searchValue = unref(search)
  if (!searchValue) {
    return props.items
  }
  const substring = searchValue.toLowerCase()
  return props.items.filter((item) => {
    const value = typeof item === 'string' ? item : item.title.toString()
    return value.toLowerCase().includes(substring)
  })
})
const hint = computed<string>(() => t('commons.search_n_items', { n: actualItems.value.length }))

watch(
  () => props.items,
  () => (search.value = undefined)
)
</script>

<template>
  <v-select
    v-model="value"
    clearable
    hide-details
    :items="actualItems"
    :label="label"
    variant="outlined"
  >
    <template #prepend-item>
      <v-list-item>
        <v-text-field
          v-model="search"
          :prepend-inner-icon="mdiMagnify"
          clearable
          :hint="hint"
          persistent-hint
          variant="outlined"
        />
      </v-list-item>
    </template>
  </v-select>
</template>
