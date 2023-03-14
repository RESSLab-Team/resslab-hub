<script setup lang="ts">
import aiscSections from '@/assets/connection/aisc-sections.csv'
import europeanSections from '@/assets/connection/european-sections.csv'
import japaneseSections from '@/assets/connection/japanese-sections.csv'
import SearchSelect from '@/components/commons/SearchSelect.vue'
import type { Section } from '@/utils/common'
import type { SelectItem } from '@/utils/vuetify'
import { computed, ref, watch } from 'vue'

const emit = defineEmits<{
  (e: 'update:section', value: Section | undefined): void
}>()

type Database = 'aisc' | 'european' | 'japanese'
const databases: Database[] = ['aisc', 'european', 'japanese']

const database = ref<Database>('aisc')
const section = ref<Section>()

const sections = computed<SelectItem<Section>[]>(() => {
  let sections: Section[]
  switch (database.value) {
    case 'aisc':
      sections = aiscSections
      break
    case 'european':
      sections = europeanSections
      break
    case 'japanese':
      sections = japaneseSections
      break
    default:
      return []
  }
  return sections.map((section) => ({
    title: section.id,
    value: section
  }))
})

watch(database, () => {
  section.value = undefined
})

watch(section, (value) => {
  emit('update:section', value)
})
</script>

<template>
  <v-row>
    <v-col cols="6">
      <v-select
        v-model="database"
        hide-details
        :items="databases"
        label="Select Database"
        variant="outlined"
      />
    </v-col>
    <v-col cols="6">
      <search-select v-model="section" :items="sections" label="Select Section" />
    </v-col>
  </v-row>
</template>
