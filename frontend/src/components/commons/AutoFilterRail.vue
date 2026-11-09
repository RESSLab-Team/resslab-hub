<script setup lang="ts">
/**
 * The filter rail: every column of the database, classified by
 * {@link AutoFilterRow} and collected into the scientific categories of
 * `utils/fieldGroups.ts`.
 *
 * The list is derived rather than curated, so it is long: connections alone has
 * 150 filters. Grouping is what makes that navigable. A reader meets eight to
 * twelve headings, opens the one they were thinking of, and the search box stays
 * as the direct route for anyone who already knows the variable's name.
 */
import AutoFilterRow from '@/components/commons/AutoFilterRow.vue'
import type { FilterGroup, LabeledFilter } from '@/composables/useAutoFilters'
import type { FieldGroupId } from '@/utils/fieldGroups'
import type { Searches, Value } from '@/utils/common'
import { mdiChevronRight, mdiClose, mdiMagnify } from '@mdi/js'
import { computed, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    groups: FilterGroup[]
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

function isActive(filter: LabeledFilter): boolean {
  return props.searches[filter.key] != null
}

/** Match the label a user sees, the column name they may know, and the
 *  dictionary description — the last one makes unlabelled fields findable. */
function matchesSearch(filter: LabeledFilter, needle: string): boolean {
  return `${filter.label} ${filter.key} ${filter.column.description}`.toLowerCase().includes(needle)
}

const visible = computed<FilterGroup[]>(() => {
  const needle = search.value.trim().toLowerCase()
  if (!needle) return props.groups
  return props.groups
    .map((group) => ({
      ...group,
      filters: group.filters.filter((filter) => matchesSearch(filter, needle))
    }))
    .filter((group) => group.filters.length > 0)
})

const activeCount = computed<number>(
  () => props.groups.flatMap((group) => group.filters).filter(isActive).length
)

function activeIn(group: FilterGroup): number {
  return group.filters.filter(isActive).length
}

// Identification is open from the start because it is the one group every reader
// wants; the others wait to be asked for.
const openGroups = ref<Set<FieldGroupId>>(new Set<FieldGroupId>(['experimental_program_details']))

/** Rows already carrying a filter, so a shared URL shows the value it filters on. */
const open = ref<Set<string>>(new Set())

// Seeded on the first non-empty groups rather than at setup: the overlay is
// mounted with the dashboard, well before the dataset has loaded and the filters
// exist, so reading props here would always see an empty list.
const seeded = ref<boolean>(false)
watch(
  () => props.groups,
  (groups) => {
    if (seeded.value || groups.length === 0) return
    seeded.value = true
    // A group already carrying a filter opens too, so an incoming (shared,
    // bookmarked) URL shows what it is filtering on without any hunting.
    groups.filter((group) => activeIn(group) > 0).forEach((group) => openGroups.value.add(group.id))
    open.value = new Set(
      groups
        .flatMap((group) => group.filters)
        .filter(isActive)
        .map((filter) => filter.key)
    )
  },
  { immediate: true }
)

// A filter set from elsewhere (a chart click, a chip, a table header, the URL) has
// to show up here, so its group and its row open. Only opening: closing stays the
// reader's gesture.
watch(
  () => Object.keys(props.searches),
  (keys, previous = []) => {
    const added = keys.filter((key) => !previous.includes(key))
    if (added.length === 0) return
    const groups = new Set(openGroups.value)
    const rows = new Set(open.value)
    for (const group of props.groups) {
      for (const filter of group.filters) {
        if (!added.includes(filter.key) || !isActive(filter)) continue
        groups.add(group.id)
        rows.add(filter.key)
      }
    }
    openGroups.value = groups
    open.value = rows
  }
)

/** While searching, every group holding a hit is open: hiding a match behind a
 *  collapsed heading would make the search box look broken. */
function isOpen(group: FilterGroup): boolean {
  return searching.value || openGroups.value.has(group.id)
}

function toggleGroup(group: FilterGroup): void {
  const next = new Set(openGroups.value)
  if (next.has(group.id)) next.delete(group.id)
  else next.add(group.id)
  openGroups.value = next
}

const searching = computed<boolean>(() => search.value.trim().length > 0)

const allOpen = computed<boolean>(() =>
  props.groups.every((group) => openGroups.value.has(group.id))
)

// Groups only, not the rows inside: a group of closed rows costs a few buttons,
// while an open row mounts its histogram.
function toggleAll(): void {
  openGroups.value = new Set(allOpen.value ? [] : props.groups.map((group) => group.id))
}

function setOpen(key: string, value: boolean): void {
  const next = new Set(open.value)
  if (value) next.add(key)
  else next.delete(key)
  open.value = next
}

function resetAll(): void {
  props.groups
    .flatMap((group) => group.filters)
    .filter(isActive)
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
        <!-- Hidden while searching: the search box decides what is open then. -->
        <button v-if="groups.length > 0 && !searching" class="expand" @click="toggleAll">
          {{ allOpen ? $t('commons.collapse_all') : $t('commons.expand_all') }}
        </button>
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
      <section v-for="group in visible" :key="group.id" class="afr-group">
        <button
          class="afr-group-head"
          :aria-expanded="isOpen(group)"
          :aria-label="
            isOpen(group)
              ? $t('shell.collapse_group', { group: group.label })
              : $t('shell.expand_group', { group: group.label })
          "
          @click="toggleGroup(group)"
        >
          <v-icon
            class="afr-group-caret"
            :class="{ open: isOpen(group) }"
            :icon="mdiChevronRight"
            size="14"
          />
          <span class="afr-group-label">{{ group.label }}</span>
          <span v-if="activeIn(group) > 0" class="afr-group-active">{{ activeIn(group) }}</span>
          <span class="afr-group-count">{{ group.filters.length }}</span>
        </button>
        <div v-if="isOpen(group)" class="afr-group-body">
          <auto-filter-row
            v-for="filter in group.filters"
            :key="filter.key"
            :filter="filter"
            :open="open.has(filter.key)"
            :value="searches[filter.key]"
            @update="(value) => emit('change:searches', filter.key, value)"
            @update:open="(value) => setOpen(filter.key, value)"
          />
        </div>
      </section>
    </div>
  </aside>
</template>
