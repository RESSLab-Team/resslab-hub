<script setup lang="ts">
import EyebrowText from '@/components/commons/EyebrowText.vue'
import FilterRail, { type FilterRailGroup } from '@/components/commons/FilterRail.vue'
import i18n from '@/plugins/i18n'
import { useNotificationStore } from '@/stores/notification'
import { shareCurrentUrl, type Searches, type Value } from '@/utils/common'
import { DATABASES, type DatabaseId } from '@/utils/navigation'
import { mdiClose, mdiFilterVariant, mdiMagnify, mdiShare } from '@mdi/js'
import { computed, ref } from 'vue'
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
    railGroups: FilterRailGroup[]
    searches: Searches
    search?: string
    searchPlaceholder?: string
    /** Whether the detail drawer is open (typically `!!item`) */
    detailOpen?: boolean
  }>(),
  {
    count: undefined,
    countLabel: 'tests',
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

const searchModel = computed<string>({
  get: () => props.search,
  set: (value) => emit('update:search', value)
})

/** The database's own icon, resolved from the single nav definition. */
const databaseIcon = computed<string | undefined>(
  () => DATABASES.find((entry) => entry.id === props.databaseId)?.icon
)

const railFilterCount = computed<number>(
  () => props.railGroups.filter((group) => props.searches[group.key] != null).length
)

/* ---- active-filter chips (mirrors the searches driving table + charts) ---- */
function formatChipValue(value: Value): string {
  if (Array.isArray(value)) {
    if (value.length === 2 && value.every((v) => !isNaN(Number(v)))) {
      return `${value[0]} – ${value[1]}`
    }
    return i18n.global.t('commons.n_selected', { n: value.length })
  }
  if (typeof value === 'boolean') {
    return value ? i18n.global.t('commons.yes') : i18n.global.t('commons.no')
  }
  const text = String(value)
  if (text.includes('<<')) {
    return text.split('<<', 2).join(' – ')
  }
  return text.length > 32 ? `${text.split(',').length} selected` : text
}

const activeChips = computed(() =>
  Object.entries(props.searches).map(([key, value]) => ({
    key,
    label: `${i18n.global.t(props.i18nPrefix + key)}: ${formatChipValue(value)}`
  }))
)

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
          </div>
          <p v-if="description" class="dash-desc">{{ description }}</p>
        </div>
        <!-- Decorative: the title already names the database. -->
        <div v-if="databaseIcon" class="dash-head-icon" aria-hidden="true">
          <v-icon :icon="databaseIcon" />
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
        <button class="btn btn-secondary btn-sm" @click="shareView">
          <v-icon :icon="mdiShare" size="14" />
          {{ $t('commons.share_view') }}
        </button>
        <button
          class="btn btn-secondary btn-sm dash-filters-trigger"
          @click="filtersOverlayOpen = true"
        >
          <v-icon :icon="mdiFilterVariant" size="14" />
          {{ $t('commons.filters') }}
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
        <span
          class="fchip-x"
          role="button"
          :aria-label="$t('commons.remove_filter', { label: chip.label })"
          @click="emit('change:searches', chip.key, undefined)"
        >
          <v-icon :icon="mdiClose" size="10" />
        </span>
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

    <!-- Chart strips -->
    <slot name="charts" />

    <!-- Detail drawer -->
    <div class="drawer-scrim" :class="{ open: detailOpen }" @click="emit('close:detail')" />
    <aside class="drawer" :class="{ open: detailOpen }">
      <slot name="detail" />
    </aside>

    <!-- Filters overlay drawer -->
    <div
      class="drawer-scrim"
      :class="{ open: filtersOverlayOpen }"
      @click="filtersOverlayOpen = false"
    />
    <aside class="filters-overlay" :class="{ open: filtersOverlayOpen }">
      <filter-rail
        as-overlay
        :groups="railGroups"
        position="right"
        :searches="searches"
        @change:searches="(key, value) => emit('change:searches', key, value)"
        @close="filtersOverlayOpen = false"
      />
    </aside>
  </div>
</template>
