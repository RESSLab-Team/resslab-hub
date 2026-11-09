<script setup lang="ts">
import EyebrowText from '@/components/commons/EyebrowText.vue'
import AutoFilterRail from '@/components/commons/AutoFilterRail.vue'
import i18n from '@/plugins/i18n'
import { useNotificationStore } from '@/stores/notification'
import type { FilterGroup, LabeledFilter } from '@/composables/useAutoFilters'
import { formatFilterValue, shareCurrentUrl, type Searches, type Value } from '@/utils/common'
import { STATUS_COLUMN, VERIFIED_ONLY_SEARCH } from '@/utils/curationStatus'
import { databases, type DatabaseId } from '@/utils/navigation'
import { mdiCheckDecagramOutline, mdiClose, mdiFilterVariant, mdiMagnify, mdiShare } from '@mdi/js'
import { useEscapeKey } from '@/composables/useEscapeKey'
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

/**
 * EPFL design-system dashboard scaffold (from the Claude Design handoff):
 * dash-head (eyebrow / title + count / Share view / description)
 * → toolbar (global search + Filters overlay trigger)
 * → active-filter chips
 * → full-bleed table (#table slot)
 * → chart strips (#charts slot)
 * → detail drawer (#detail slot) and filters overlay.
 */
const props = withDefaults(
  defineProps<{
    eyebrow: string
    title: string
    count?: number
    countLabel?: string
    description?: string
    /** i18n key prefix for the active-filter chip labels, e.g. 'connection.' */
    i18nPrefix: string
    /** Identifies the database so the header can show its icon (see navigation.ts). */
    databaseId?: DatabaseId
    /** Auto-generated filter descriptors (see useAutoFilters), flat, for the chips. */
    filters: LabeledFilter[]
    /** The same filters split into scientific categories, for the rail. */
    filterGroups: FilterGroup[]
    filtersLoading?: boolean
    searches: Searches
    search?: string
    searchPlaceholder?: string
    /** Whether the detail drawer is open (typically `!!item`) */
    detailOpen?: boolean
  }>(),
  {
    count: undefined,
    countLabel: 'tests',
    filtersLoading: false,
    description: undefined,
    databaseId: undefined,
    search: '',
    searchPlaceholder: 'Search all columns…',
    detailOpen: false
  }
)
const emit = defineEmits<{
  (e: 'update:search', value: string): void
  (e: 'change:searches', key: string, value?: Value): void
  (e: 'close:detail'): void
}>()

const route = useRoute()
const notificationStore = useNotificationStore()

const filtersOverlayOpen = ref<boolean>(false)

/* ---- drawers and the keyboard ---- */
// Escape closes the top drawer: the filters overlay first, then the detail one.
useEscapeKey(
  computed(() => props.detailOpen || filtersOverlayOpen.value),
  () => {
    if (filtersOverlayOpen.value) filtersOverlayOpen.value = false
    else emit('close:detail')
  }
)

// A closed drawer is `inert`, so the focus inside it would drop to <body> on
// close. Move it into the drawer on open, and back to where it was on close
// (the table row that opened it).
const detailDrawer = ref<HTMLElement>()
let focusBeforeDetail: HTMLElement | null = null
watch(
  () => props.detailOpen,
  async (open) => {
    if (open) {
      focusBeforeDetail ??= document.activeElement as HTMLElement | null
      await nextTick()
      detailDrawer.value?.focus({ preventScroll: true })
    } else {
      if (focusBeforeDetail?.isConnected) focusBeforeDetail.focus({ preventScroll: true })
      focusBeforeDetail = null
    }
  }
)

const searchModel = computed<string>({
  get: () => props.search,
  set: (value) => emit('update:search', value)
})

/** The database's own icon, resolved from the single nav definition. */
const databaseIcon = computed<string | undefined>(
  () => databases().find((entry) => entry.id === props.databaseId)?.icon
)

const railFilterCount = computed<number>(
  () => props.filters.filter((filter) => props.searches[filter.key] != null).length
)

/* ---- active-filter chips (mirrors the searches driving table + charts) ---- */
// Most columns have no curated translation now that every one of them is
// filterable, so fall back to the label the rail resolved from the dictionary.
const activeChips = computed(() =>
  Object.entries(props.searches).map(([key, value]) => {
    // The review status is not in the rail (filterProfile's DENYLIST), so it
    // has no dictionary label there: name the toggle instead.
    if (key === STATUS_COLUMN && value === VERIFIED_ONLY_SEARCH) {
      return { key, label: i18n.global.t('commons.unverified.verified_only') }
    }
    if (key === STATUS_COLUMN) {
      const status = i18n.global.t('commons.unverified.status_label')
      return { key, label: `${status}: ${formatFilterValue(value, i18n.global.t)}` }
    }
    const filter = props.filters.find((entry) => entry.key === key)
    const label = filter?.label ?? i18n.global.t(props.i18nPrefix + key)
    return { key, label: `${label}: ${formatFilterValue(value, i18n.global.t)}` }
  })
)

/* ---- "Verified only" (#253): off by default, the URL carries it like any filter ---- */
const verifiedOnly = computed<boolean>(() => props.searches[STATUS_COLUMN] === VERIFIED_ONLY_SEARCH)

function toggleVerifiedOnly(): void {
  emit('change:searches', STATUS_COLUMN, verifiedOnly.value ? undefined : VERIFIED_ONLY_SEARCH)
}

function clearAll(): void {
  emit('update:search', '')
  Object.keys(props.searches).forEach((key) => emit('change:searches', key, undefined))
}

function shareView(): void {
  shareCurrentUrl(route.fullPath, notificationStore.notify)
}
</script>

<template>
  <div class="dash">
    <!-- Ultrawide (≥2100px) splits header + table from the charts, which then
         pin beside the scrolling table. Below that the wrappers are
         `display: contents`, so everything stacks as before. -->
    <div class="dash-split">
      <div class="dash-col-main">
        <!-- Page header -->
        <div class="dash-head">
          <div class="eyebrow" style="margin-bottom: 6px"><eyebrow-text :text="eyebrow" /></div>
          <div class="dash-head-split">
            <div class="dash-head-main">
              <div class="dash-head-row">
                <h1 class="dash-title">
                  {{ title }}
                  <span v-if="count != null" class="dash-title-count">
                    {{ count.toLocaleString('en-CH') }}
                    {{ countLabel === 'tests' ? $t('commons.dash_count_label') : countLabel }}
                  </span>
                </h1>
                <div class="dash-head-actions">
                  <slot name="head-actions" />
                </div>
                <!-- Decorative: the title already names the database. Lives in the
                     title row so it sits beside the title once it stops being
                     absolutely positioned on narrow screens. -->
                <div v-if="databaseIcon" class="dash-head-icon" aria-hidden="true">
                  <v-icon :icon="databaseIcon" />
                </div>
              </div>
              <p v-if="description" class="dash-desc">{{ description }}</p>
            </div>
          </div>
        </div>

        <!-- Toolbar: global search + filters -->
        <div class="dash-toolbar">
          <div class="dash-search">
            <v-icon class="dash-search-icon" :icon="mdiMagnify" size="16" />
            <input
              v-model="searchModel"
              type="search"
              :placeholder="
                searchPlaceholder === 'Search all columns…'
                  ? $t('commons.dash_search_placeholder')
                  : searchPlaceholder
              "
            />
          </div>
          <div class="dash-toolbar-spacer" />
          <div class="dash-toolbar-actions">
            <button
              v-if="databaseId"
              class="btn btn-secondary btn-sm dash-verified-toggle"
              :class="{ 'is-on': verifiedOnly }"
              :aria-pressed="verifiedOnly"
              :title="$t('commons.unverified.verified_only_hint')"
              @click="toggleVerifiedOnly"
            >
              <v-icon :icon="mdiCheckDecagramOutline" size="14" />
              {{ $t('commons.unverified.verified_only') }}
            </button>
            <button class="btn btn-secondary btn-sm" @click="shareView">
              <v-icon :icon="mdiShare" size="14" />
              {{ $t('commons.share_view') }}
            </button>
            <button
              class="btn btn-secondary btn-sm dash-filters-trigger"
              @click="filtersOverlayOpen = true"
            >
              <v-icon :icon="mdiFilterVariant" size="14" />
              <!-- "All", not just "Filters": the rail holds every column of the
                   database, which the toolbar's own search box does not hint at. -->
              {{ $t('commons.all_filters') }}
              <span v-if="railFilterCount > 0" class="dash-filters-trigger-badge">
                {{ railFilterCount }}
              </span>
            </button>
          </div>
        </div>

        <!-- Active filters -->
        <div v-if="activeChips.length > 0" class="dash-active-filters">
          <strong>{{ $t('commons.active_filters') }}</strong>
          <span v-for="chip in activeChips" :key="chip.key" class="fchip">
            {{ chip.label }}
            <button
              class="fchip-x"
              type="button"
              :aria-label="$t('commons.remove_filter', { label: chip.label })"
              @click="emit('change:searches', chip.key, undefined)"
            >
              <v-icon :icon="mdiClose" size="10" />
            </button>
          </span>
          <button class="chip-clear" @click="clearAll">
            <v-icon :icon="mdiClose" size="10" />
            {{ $t('commons.clear_all') }}
          </button>
        </div>

        <!-- Table (full bleed) -->
        <div class="dash-table-full">
          <slot name="table" />
        </div>
      </div>
      <div class="dash-col-side">
        <!-- Chart strips -->
        <slot name="charts" />
      </div>
    </div>

    <!-- Detail drawer -->
    <button
      class="drawer-scrim"
      type="button"
      :class="{ open: detailOpen }"
      :aria-label="$t('commons.close')"
      :inert="!detailOpen || undefined"
      @click="emit('close:detail')"
    />
    <aside
      ref="detailDrawer"
      class="drawer"
      :class="{ open: detailOpen }"
      :inert="!detailOpen || undefined"
      tabindex="-1"
    >
      <slot name="detail" />
    </aside>

    <!-- Filters overlay drawer -->
    <button
      class="drawer-scrim"
      type="button"
      :class="{ open: filtersOverlayOpen }"
      :aria-label="$t('commons.close')"
      :inert="!filtersOverlayOpen || undefined"
      @click="filtersOverlayOpen = false"
    />
    <aside
      class="filters-overlay"
      :class="{ open: filtersOverlayOpen }"
      :inert="!filtersOverlayOpen || undefined"
    >
      <auto-filter-rail
        :groups="filterGroups"
        :loading="filtersLoading"
        :searches="searches"
        @change:searches="(key, value) => emit('change:searches', key, value)"
        @close="filtersOverlayOpen = false"
      />
    </aside>
  </div>
</template>
