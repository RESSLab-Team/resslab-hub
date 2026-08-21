<script setup lang="ts">
/**
 * The filter rail: every column of the database, classified and rendered by
 * {@link AutoFilterRow}. Because the list is derived rather than curated it is
 * long, so it opens with a search box — finding a variable by name is the
 * primary way in, and scrolling the secondary one.
 */
import AutoFilterRow from '@/components/commons/AutoFilterRow.vue'
import type { LabeledFilter } from '@/composables/useAutoFilters'
import type { Searches, Value } from '@/utils/common'
import { mdiClose, mdiMagnify } from '@mdi/js'
import { computed, ref } from 'vue'

const props = withDefaults(
  defineProps<{
    filters: LabeledFilter[]
    searches: Searches
    loading?: boolean
  }>(),
  { loading: false }
)
const emit = defineEmits<{
  (e: 'change:searches', key: string, value?: Value): void
  (e: 'close'): void
}>()

const search = ref<string>('')

/** Match the label a user sees, the column name they may know, and the
 *  dictionary description — the last one makes unlabelled fields findable. */
const visible = computed<LabeledFilter[]>(() => {
  const needle = search.value.trim().toLowerCase()
  if (!needle) return props.filters
  return props.filters.filter((filter) =>
    `${filter.label} ${filter.key} ${filter.column.description}`.toLowerCase().includes(needle)
  )
})

const activeCount = computed<number>(
  () => props.filters.filter((filter) => props.searches[filter.key] != null).length
)

// Rows already carrying a filter start open, so an incoming (shared, bookmarked)
// URL shows what it is filtering on without any hunting.
const open = ref<Set<string>>(
  new Set(props.filters.filter((filter) => props.searches[filter.key] != null).map((f) => f.key))
)

function setOpen(key: string, value: boolean): void {
  const next = new Set(open.value)
  if (value) next.add(key)
  else next.delete(key)
  open.value = next
}

function resetAll(): void {
  props.filters
    .filter((filter) => props.searches[filter.key] != null)
    .forEach((filter) => emit('change:searches', filter.key, undefined))
}
</script>

<template>
  <aside class="dash-filters dash-filters-overlay afr">
    <div class="dash-filters-head">
      <div class="dash-filters-head-l">
        <h6>{{ $t('commons.filters') }}</h6>
        <span v-if="activeCount > 0" class="dash-filters-active-count">{{ activeCount }}</span>
      </div>
      <div class="dash-filters-head-r">
        <button class="reset" @click="resetAll">{{ $t('commons.reset_all') }}</button>
        <button
          class="dash-filters-collapse-btn"
          :title="$t('commons.close_filters')"
          :aria-label="$t('commons.close_filters')"
          @click="emit('close')"
        >
          <v-icon :icon="mdiClose" size="14" />
        </button>
      </div>
    </div>

    <div class="afr-search">
      <v-icon class="afr-search-icon" :icon="mdiMagnify" size="15" />
      <input v-model="search" type="search" :placeholder="$t('commons.find_a_variable')" />
    </div>

    <p v-if="loading" class="afr-empty">{{ $t('commons.loading_filters') }}</p>
    <p v-else-if="visible.length === 0" class="afr-empty">{{ $t('commons.no_variables_found') }}</p>

    <div class="afr-list">
      <auto-filter-row
        v-for="filter in visible"
        :key="filter.key"
        :filter="filter"
        :open="open.has(filter.key)"
        :value="searches[filter.key]"
        @update="(value) => emit('change:searches', filter.key, value)"
        @update:open="(value) => setOpen(filter.key, value)"
      />
    </div>
  </aside>
</template>
