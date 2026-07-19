<script setup lang="ts">
import connectionAiscSections from '@/assets/connection/aisc-sections.csv'
import connectionEuropeanSections from '@/assets/connection/european-sections.csv'
import connectionJapaneseSections from '@/assets/connection/japanese-sections.csv'
import hssAiscSections from '@/assets/hss/hss-aisc-sections.csv'
import hssEuropeanSections from '@/assets/hss/hss-european-sections.csv'
import hssJapaneseSections from '@/assets/hss/hss-japanese-sections.csv'
import SearchSelect from '@/components/commons/SearchSelect.vue'
import type { HSSSection, Section } from '@/utils/common'
import type { SelectItem } from '@/utils/vuetify'
import { computed, ref, watch } from 'vue'

const emit = defineEmits<{
  (e: 'update:section', value: Section | undefined): void
}>()

const props = withDefaults(
  defineProps<{
    source?: string
  }>(),
  {
    source: 'connection'
  }
)

type Database = 'aisc' | 'european' | 'japanese'
const databaseItems: SelectItem<Database>[] = [
  { title: 'AISC', value: 'aisc' },
  { title: 'European', value: 'european' },
  { title: 'Japanese', value: 'japanese' }
]

const database = ref<Database>('aisc')
const section = ref<Section>()

const sections = computed<SelectItem<Section | HSSSection>[]>(() => {
  let sections: (Section | HSSSection)[]
  switch (database.value) {
    case 'aisc':
      sections = props.source == 'connection' ? connectionAiscSections : hssAiscSections
      break
    case 'european':
      sections = props.source == 'connection' ? connectionEuropeanSections : hssEuropeanSections
      break
    case 'japanese':
      sections = props.source == 'connection' ? connectionJapaneseSections : hssJapaneseSections
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
  <div class="section-selector">
    <v-select
      v-model="database"
      hide-details
      :items="databaseItems"
      :label="$t('commons.select_database')"
      variant="outlined"
    />
    <search-select v-model="section" :items="sections" :label="$t('commons.select_section')" />
  </div>
</template>

<style scoped>
.section-selector {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
</style>
