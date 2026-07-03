<script setup lang="ts" generic="M extends { id: string }">
import CheckboxDialog, { type CheckBoxDialogItem } from '@/components/commons/CheckboxDialog.vue'
import TextSubscript from '@/components/commons/TextSubscript.vue'
import { DownloadType, type Column, type ColumnType } from '@/composables/table'
import { useVirtualRows } from '@/composables/useVirtualRows'
import i18n from '@/plugins/i18n'
import { useNotificationStore } from '@/stores/notification'
import { shareCurrentUrl, type Searches } from '@/utils/common'
import type { DataOptions } from '@/utils/vuetify'
import { booleanOptions } from '@/utils/vuetify'
import { mdiDownload, mdiMagnify, mdiMenuDown, mdiMenuUp, mdiShare } from '@mdi/js'
import { computed, onMounted, onUnmounted, ref, shallowRef, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'

interface TableHeader {
  type: ColumnType
  multiple?: boolean
  options?: string[]
  format?: (value: unknown) => string
  cellVariant?: 'mono' | 'tag' | 'strong'
  // https://github.com/vuetifyjs/vuetify/blob/master/packages/vuetify/src/labs/VDataTable/types.ts
  key: string
  title: string
  align?: 'start' | 'end'
}

const props = withDefaults(
  defineProps<{
    title?: string
    columns?: Column[]
    totalCount?: number
    loading?: boolean
    items?: M[]
    totalFilteredCount?: number
    prefix?: string
    query?: string
    searches?: Searches
    search?: string
    /** Hide the filter-only inputs row above the table (when a filter rail covers them) */
    hideFilterOnly?: boolean
    /** Hide the title/search toolbar (when the dashboard provides its own toolbar) */
    hideToolbar?: boolean
    /** In-browser filtering is instant — skip the loading bar that reads as a fetch. */
    instant?: boolean
    /** Provisional filtered count shown live during a crossfilter drag. Display-only:
     *  it feeds the footer text but NOT pagination or the row list. Cleared
     *  (undefined) when not dragging. */
    liveCount?: number
    /** Live page rows streamed during a crossfilter drag. When set, they replace
     *  the committed `items` in the body (the light-DOM rows are cheap enough to
     *  re-render every frame). Cleared (undefined) on drag end → back to `items`. */
    liveItems?: M[]
  }>(),
  {
    title: undefined,
    columns: () => [],
    totalCount: undefined,
    loading: false,
    items: () => [],
    totalFilteredCount: 0,
    prefix: undefined,
    query: undefined,
    searches: () => ({}),
    search: '',
    hideFilterOnly: false,
    hideToolbar: false,
    instant: false,
    liveCount: undefined,
    liveItems: undefined
  }
)
const emit = defineEmits<{
  (e: 'click:row', value: M): void
  (e: 'download', items: M[], types: DownloadType[]): void
  (e: 'update:options', value?: DataOptions): void
  (e: 'update:search', value: string): void
  (e: 'update:searches', value: Searches): void
}>()

const maxDownloadCount = 5
const itemsPerPageOptions = [5, 10, 20, 100, 1000]
const vInputBind = {
  class: 'table-input',
  clearable: true,
  density: 'compact' as 'compact',
  hideDetails: true,
  singleLine: true,
  variant: 'underlined' as 'underlined'
}
// Design-handoff bordered inputs for the in-thead filter row (border comes from CSS)
const vTheadInputBind = {
  ...vInputBind,
  variant: 'plain' as 'plain'
}
const { t } = useI18n({ useScope: 'global' })
const checkboxDialogItems: CheckBoxDialogItem<DownloadType>[] = [
  {
    key: DownloadType.Main,
    text: t('commons.download_master_data')
  },
  {
    key: DownloadType.Test,
    text: t('commons.download_test_data')
  }
]

const route = useRoute()
const notificationStore = useNotificationStore()

const downloadDialog = ref<InstanceType<typeof CheckboxDialog>>()
const selectedItemsIds = ref<string[]>([])
// shallowRef, and not just for performance: a deep ref would unwrap the generic
// M (UnwrapRefSimple<M>) and break the typing of everything touching it.
const selectedItems = shallowRef<M[]>([])
const page = ref<number>(1)
const itemsPerPage = ref<number>(5)
const sortBy = ref<{ key: string; order: 'asc' | 'desc' }>()

// Rows shown in the body: live drag frames replace the committed page while a
// brush is being dragged, otherwise the reactive page from the server/dataset.
const displayItems = computed<M[]>(() => props.liveItems ?? props.items)

// The loading bar only appears if the fetch outlives SHOW_DELAY_MS — a load
// served from cache (browser HTTP cache, or the in-memory dataset cache on SPA
// back-navigation) resolves faster than that and must not flash a bar at all.
// Once shown it stays at least MIN_LOADING_MS (one full 1s march below, so the
// bar reaches the far edge before fading) even if `loading` already went false;
// a new fetch in the meantime cancels the hide timer and persists the bar.
const SHOW_DELAY_MS = 150
const MIN_LOADING_MS = 1000
const showLoading = ref<boolean>(false)
let loadingShownAt = 0
let showLoadingTimer: ReturnType<typeof setTimeout> | undefined
let hideLoadingTimer: ReturnType<typeof setTimeout> | undefined
// Instant (in-browser) tables fetch the whole dataset once, then filter locally.
// The loading bar should still mark that initial fetch, but the synchronous filter
// re-slices afterwards must not flash it (they'd trip the 1s minimum on every
// keystroke). So suppress the bar only AFTER the first load has completed.
let initialLoadDone = false
watch(
  () => props.loading,
  (isLoading, wasLoading) => {
    if (props.instant && initialLoadDone) return
    if (isLoading) {
      if (hideLoadingTimer) {
        clearTimeout(hideLoadingTimer)
        hideLoadingTimer = undefined
      }
      if (!showLoading.value && !showLoadingTimer) {
        showLoadingTimer = setTimeout(() => {
          showLoadingTimer = undefined
          showLoading.value = true
          loadingShownAt = Date.now()
        }, SHOW_DELAY_MS)
      }
    } else {
      // Load finished before the bar appeared: a cache hit — never show it.
      if (showLoadingTimer) {
        clearTimeout(showLoadingTimer)
        showLoadingTimer = undefined
      }
      // A load just finished (true → false): the initial fetch is done, so
      // instant tables suppress the bar from here on.
      if (wasLoading) initialLoadDone = true
      if (showLoading.value) {
        const remaining = MIN_LOADING_MS - (Date.now() - loadingShownAt)
        if (remaining <= 0) {
          showLoading.value = false
        } else {
          hideLoadingTimer = setTimeout(() => {
            showLoading.value = false
            hideLoadingTimer = undefined
          }, remaining)
        }
      }
    }
  },
  { immediate: true }
)

// Size the loading shimmer to the table head only. The header height is stable
// per dashboard but varies between them, so measure the real <thead> and track it
// via ResizeObserver. (The header sticks as a whole unit — no per-row offset.)
const scrollEl = ref<HTMLElement>()
const headHeight = ref<string>('86px')
let headObserver: ResizeObserver | undefined
function measureHead(): void {
  const thead = scrollEl.value?.querySelector('thead') as HTMLElement | null
  if (thead) headHeight.value = `${thead.offsetHeight}px`
}

onMounted(() => {
  // Default sort — mirrors Vuetify's `must-sort` initial state and, crucially,
  // emits the first `update:options` that kicks the initial page fetch.
  if (!sortBy.value && tableHeaders.value.length) {
    sortBy.value = { key: tableHeaders.value[0].key, order: 'asc' }
  }
  emitOptions()
  // Watch for subsequent sort/page/size changes — registered after the initial
  // emit so the default-sort assignment above doesn't double-fire it. (Created in
  // onMounted, still bound to this instance's scope, so it's disposed on unmount.)
  watch([sortBy, page, itemsPerPage], emitOptions, { deep: true })

  measureHead()
  const thead = scrollEl.value?.querySelector('thead') as HTMLElement | null
  if (thead && 'ResizeObserver' in window) {
    headObserver = new ResizeObserver(measureHead)
    headObserver.observe(thead)
  }
})
onUnmounted(() => {
  if (showLoadingTimer) clearTimeout(showLoadingTimer)
  if (hideLoadingTimer) clearTimeout(hideLoadingTimer)
  headObserver?.disconnect()
})

// Row virtualization: window the current page's rows so large page sizes
// (100/1000) mount only what's visible. No-ops for the common small pages.
const totalRows = computed<number>(() => displayItems.value.length)
const { window: rowWindow } = useVirtualRows(scrollEl, totalRows)
const visibleRows = computed<M[]>(() =>
  displayItems.value.slice(rowWindow.value.startIndex, rowWindow.value.endIndex)
)

watch(selectedItemsIds, (newIdList, oldIdList) => {
  const oldList = selectedItems.value
  const newIds = newIdList.filter((id) => !oldIdList.includes(id)),
    removedIds = oldIdList.filter((id) => !newIdList.includes(id))
  const newList = oldList
    .filter((item) => !removedIds.includes(item.id))
    .concat(
      newIds
        // Resolve against what is actually rendered (live drag rows when set),
        // falling back to the committed page — a row selected mid-drag may not
        // exist in `props.items` yet and would otherwise be silently dropped.
        .map(
          (id) =>
            displayItems.value.find((item) => item.id === id) ??
            props.items.find((item) => item.id === id)
        )
        .filter((item): item is M => item !== undefined)
    )
  selectedItems.value = newList
})

const columnSearches = computed<Searches>({
  get: () => props.searches,
  set: (value) => emit('update:searches', value)
})
const globalSearch = computed<string>({
  get: () => props.search,
  set: (value) => emit('update:search', value)
})
const tableHeaders = computed<TableHeader[]>(() =>
  props.columns.filter((column) => !column.filterOnly).map(getTableHeader)
)
const filterHeaders = computed<TableHeader[]>(() =>
  props.columns.filter((column) => column.filterOnly).map(getTableHeader)
)
const hasFilters = computed<boolean>(() => !!props.query && props.query?.length != 0)

// Fixed-layout column proportions: text/option columns get twice the share of
// numeric/boolean. Widths are a fraction of the space left by the fixed 44px
// select column, so they sum to exactly 100% — the whole table fits the container
// with no horizontal overflow, and long headers/values ellipsis within their cell.
const columnWidths = computed<string[]>(() => {
  const weights = tableHeaders.value.map((h) => (h.type === 'text' || h.type === 'option' ? 2 : 1))
  const total = weights.reduce((sum, w) => sum + w, 0) || 1
  return weights.map((w) => `calc((100% - 44px) * ${(w / total).toFixed(4)})`)
})

const pageCount = computed<number>(() =>
  Math.max(1, Math.ceil(props.totalFilteredCount / itemsPerPage.value))
)
const pageFrom = computed<number>(() =>
  props.totalFilteredCount === 0 ? 0 : (page.value - 1) * itemsPerPage.value + 1
)
const pageTo = computed<number>(() =>
  Math.min(page.value * itemsPerPage.value, props.totalFilteredCount)
)
// Footer "showing X to Y of Z" values, overridden by the live drag count when set
// (display-only — pagination above still uses the committed totalFilteredCount).
const displayTotal = computed<number>(() => props.liveCount ?? props.totalFilteredCount)
const displayTo = computed<number>(() =>
  props.liveCount != null ? Math.min(pageTo.value, props.liveCount) : pageTo.value
)
// Design-handoff pager: 1 … around current … last, with ellipsis gaps
const pageItems = computed<(number | '…')[]>(() => {
  const last = pageCount.value
  const current = page.value
  if (last <= 7) {
    return Array.from({ length: last }, (_, index) => index + 1)
  }
  const pages = new Set<number>([1, last])
  for (let p = current - 1; p <= current + 1; p++) {
    if (p >= 1 && p <= last) {
      pages.add(p)
    }
  }
  const sorted = [...pages].sort((a, b) => a - b)
  const items: (number | '…')[] = []
  sorted.forEach((p, index) => {
    if (index > 0 && p - sorted[index - 1] > 1) {
      items.push('…')
    }
    items.push(p)
  })
  return items
})

watch(pageCount, (value) => {
  if (page.value > value) {
    page.value = value
  }
})

watch(selectedItems, (value) => {
  if (value.length >= maxDownloadCount) {
    notificationStore.notify(t('commons.max_download', { max: maxDownloadCount }))
  }
})

// Sort / page / size are owned here and pushed to the parent via `update:options`,
// exactly as `v-data-table-server` used to — `useTable` re-fetches from them.
function emitOptions(): void {
  emit('update:options', {
    sortBy: sortBy.value ? [sortBy.value] : [],
    page: page.value,
    itemsPerPage: itemsPerPage.value
  })
}

function toggleSort(header: TableHeader): void {
  // `must-sort`: a column is never returned to the unsorted state — clicking the
  // active column flips direction, a new column sorts ascending.
  if (sortBy.value?.key === header.key) {
    sortBy.value = { key: header.key, order: sortBy.value.order === 'asc' ? 'desc' : 'asc' }
  } else {
    sortBy.value = { key: header.key, order: 'asc' }
  }
}

function isItemSelectable(item: M): boolean {
  return selectedItems.value.length < maxDownloadCount || selectedItemsIds.value.includes(item.id)
}
function isRowSelected(item: M): boolean {
  return selectedItemsIds.value.includes(item.id)
}
function toggleRow(item: M): void {
  if (isRowSelected(item)) {
    selectedItemsIds.value = selectedItemsIds.value.filter((id) => id !== item.id)
  } else if (isItemSelectable(item)) {
    selectedItemsIds.value = [...selectedItemsIds.value, item.id]
  }
}
// Header select-all across the current page, capped at the download limit.
const allPageSelected = computed<boolean>(
  () => displayItems.value.length > 0 && displayItems.value.every((item) => isRowSelected(item))
)
const somePageSelected = computed<boolean>(
  () => !allPageSelected.value && displayItems.value.some((item) => isRowSelected(item))
)
function toggleSelectAll(): void {
  if (allPageSelected.value) {
    const pageIds = new Set(displayItems.value.map((item) => item.id))
    selectedItemsIds.value = selectedItemsIds.value.filter((id) => !pageIds.has(id))
    return
  }
  const set = new Set(selectedItemsIds.value)
  for (const item of displayItems.value) {
    if (set.size >= maxDownloadCount) break
    set.add(item.id)
  }
  selectedItemsIds.value = [...set]
}

function cellText(header: TableHeader, item: M): string {
  const value = (item as Record<string, unknown>)[header.key]
  if (value === null || value === undefined) return ''
  return header.format ? header.format(value) : String(value)
}

// Plain-text header (strips the <sub> markup TextSubscript renders) for the
// hover tooltip, so an ellipsised column header stays readable.
function headerTitle(text: string): string {
  return text.replace(/<\/?sub>/g, '')
}

function resetFilters(): void {
  globalSearch.value = ''
  columnSearches.value = {}
}

function rowClick(item: M): void {
  emit('click:row', item)
}

function shareUrl(): void {
  // the URL query is added automatically via vue-router
  shareCurrentUrl(route.fullPath, notificationStore.notify)
}

function getTableHeader(column: Column): TableHeader {
  return {
    key: column.value,
    title: column.title ?? i18n.global.t(props.prefix + column.value).toString(),
    type: column.type,
    format: column.format,
    cellVariant: column.cellVariant,
    options: column.options?.sort(),
    multiple: column.options ? column.options.length > 2 : false,
    align: column.type === 'number' ? 'end' : 'start'
  }
}

/**
 * Open download dialog for option selection, get files from backend, zip them and download the zip
 */
function downloadZip(): void {
  downloadDialog.value
    ?.open(`${selectedItems.value.length} selected`)
    .then((types) => emit('download', selectedItems.value, types as DownloadType[]))
    .finally(() => {
      downloadDialog.value?.close()
    })
}
</script>

<template>
  <v-card class="stbl" flat :style="{ '--stbl-rows': String(itemsPerPage) }">
    <div v-if="!hideToolbar" class="stbl-toolbar">
      <div class="stbl-title">
        <slot name="title">
          {{ title }}
        </slot>
      </div>
      <v-spacer />
      <v-responsive class="stbl-search" max-width="280">
        <v-text-field
          v-model="globalSearch"
          clearable
          density="compact"
          hide-details
          single-line
          :prepend-inner-icon="mdiMagnify"
          :label="$t('commons.search')"
          variant="outlined"
        />
      </v-responsive>
      <button class="btn btn-ghost btn-sm" :disabled="!hasFilters" @click="resetFilters">
        {{ $t('commons.reset_filters') }}
      </button>
    </div>

    <!-- Filter-only inputs (columns not shown in the table body) -->
    <div v-if="!hideFilterOnly && filterHeaders.length" class="stbl-filteronly">
      <v-row class="px-4 pb-4">
        <v-col v-for="header in filterHeaders" :key="header.key">
          <v-select
            v-if="header.options"
            v-bind="vInputBind"
            :model-value="(columnSearches[header.key] as string)"
            :multiple="header.multiple"
            :items="header.options"
            @update:model-value="columnSearches[header.key] = $event"
          >
            <template #label> <text-subscript :text="header.title"></text-subscript> </template>
          </v-select>
          <v-text-field
            v-else-if="header.type === 'text'"
            v-bind="vInputBind"
            v-model="columnSearches[header.key]"
          >
            <template #label> <text-subscript :text="header.title"></text-subscript> </template>
          </v-text-field>
          <v-select
            v-else-if="header.type === 'boolean'"
            v-bind="vInputBind"
            v-model="columnSearches[header.key]"
            :items="booleanOptions"
          >
            <template #label> <text-subscript :text="header.title"></text-subscript> </template>
          </v-select>
          <v-text-field
            v-else-if="header.type === 'number'"
            v-bind="vInputBind"
            v-model="columnSearches[header.key]"
            type="number"
          >
            <template #label> <text-subscript :text="header.title"></text-subscript> </template>
          </v-text-field>
        </v-col>
      </v-row>
    </div>

    <div class="stbl-body">
      <div ref="scrollEl" class="stbl-scroll">
        <table class="stbl-table">
          <colgroup>
            <col class="stbl-col-select" />
            <col
              v-for="(header, index) in tableHeaders"
              :key="header.key"
              :style="{ width: columnWidths[index] }"
            />
          </colgroup>
          <thead>
            <tr class="stbl-head-titles">
              <th class="stbl-col-select">
                <input
                  type="checkbox"
                  class="stbl-check"
                  :checked="allPageSelected"
                  :indeterminate.prop="somePageSelected"
                  aria-label="select all"
                  @change="toggleSelectAll"
                />
              </th>
              <th
                v-for="header in tableHeaders"
                :key="header.key"
                class="stbl-th"
                :class="{ 'text-end': header.align === 'end', 'is-sorted': sortBy?.key === header.key }"
                :title="headerTitle(header.title)"
                @click="toggleSort(header)"
              >
                <span class="stbl-th-inner">
                  <span class="stbl-th-label"><text-subscript :text="header.title" /></span>
                  <v-icon
                    v-if="sortBy?.key === header.key"
                    class="stbl-sort"
                    size="14"
                    :icon="sortBy?.order === 'asc' ? mdiMenuUp : mdiMenuDown"
                  />
                </span>
              </th>
            </tr>
            <tr class="stbl-head-filters">
              <td class="stbl-col-select">
                <v-icon :icon="mdiMagnify" />
              </td>
              <td v-for="header in tableHeaders" :key="header.key">
                <v-select
                  v-if="header.options"
                  v-bind="vTheadInputBind"
                  :model-value="(columnSearches[header.key] as string)"
                  :label="header.title"
                  :multiple="header.multiple"
                  :items="header.options"
                  @update:model-value="columnSearches[header.key] = $event"
                >
                  <!-- eslint-disable vue/no-template-shadow -->
                  <template
                    v-if="$slots[`header-select-item.${header.key}`]"
                    #item="{ item, index, props }"
                  >
                    <!-- eslint-enable vue/no-template-shadow -->
                    <slot
                      :name="`header-select-item.${header.key}`"
                      :item="item"
                      :index="index"
                      :props="props"
                    />
                  </template>
                </v-select>
                <v-text-field
                  v-else-if="header.type === 'text'"
                  v-bind="vTheadInputBind"
                  v-model="columnSearches[header.key]"
                  :label="header.title"
                >
                  <template #label> <text-subscript :text="header.title"></text-subscript> </template>
                </v-text-field>
                <v-select
                  v-else-if="header.type === 'boolean'"
                  v-bind="vTheadInputBind"
                  v-model="columnSearches[header.key]"
                  :label="header.title"
                  :items="booleanOptions"
                >
                  <template #label> <text-subscript :text="header.title"></text-subscript> </template>
                </v-select>
                <v-text-field
                  v-else-if="header.type === 'number'"
                  v-bind="vTheadInputBind"
                  v-model="columnSearches[header.key]"
                  :label="header.title"
                  type="number"
                >
                  <template #label> <text-subscript :text="header.title"></text-subscript> </template>
                </v-text-field>
              </td>
            </tr>
          </thead>
          <tbody>
            <tr v-if="rowWindow.padTop" class="stbl-spacer" :style="{ height: `${rowWindow.padTop}px` }">
              <td :colspan="tableHeaders.length + 1"></td>
            </tr>
            <tr
              v-for="item in visibleRows"
              :key="item.id"
              class="stbl-row"
              :class="{ 'is-selected': isRowSelected(item) }"
              @click="rowClick(item)"
            >
              <td class="stbl-col-select" @click.stop>
                <input
                  type="checkbox"
                  class="stbl-check"
                  :checked="isRowSelected(item)"
                  :disabled="!isItemSelectable(item)"
                  @change="toggleRow(item)"
                />
              </td>
              <td
                v-for="header in tableHeaders"
                :key="header.key"
                :title="cellText(header, item)"
                :class="{ 'text-end': header.align === 'end' }"
              >
                <span
                  v-if="header.cellVariant === 'tag' && cellText(header, item)"
                  class="tag"
                  >{{ cellText(header, item) }}</span
                >
                <span
                  v-else
                  :class="{
                    'cell-mono': header.cellVariant === 'mono',
                    'cell-strong': header.cellVariant === 'strong'
                  }"
                  >{{ cellText(header, item) }}</span
                >
              </td>
            </tr>
            <tr
              v-if="rowWindow.padBottom"
              class="stbl-spacer"
              :style="{ height: `${rowWindow.padBottom}px` }"
            >
              <td :colspan="tableHeaders.length + 1"></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div
        class="stbl-loading"
        :class="{ 'is-loading': showLoading }"
        :style="{ height: headHeight }"
        aria-hidden="true"
      />
    </div>

    <!-- Design-handoff pager -->
    <div class="dash-pager">
      <div class="dash-pager-actions">
        <button
          class="btn btn-secondary btn-sm"
          :disabled="selectedItems.length === 0 || selectedItems.length > maxDownloadCount"
          @click="downloadZip"
        >
          <v-icon :icon="mdiDownload" size="14" />
          {{ $t('commons.download_n', { n: selectedItems.length, m: totalCount }) }}
        </button>
        <button
          v-if="!hideToolbar"
          class="btn btn-secondary btn-sm"
          :disabled="!hasFilters"
          @click="shareUrl"
        >
          <v-icon :icon="mdiShare" size="14" />
          {{ $t('commons.share') }}
        </button>
      </div>
      <div class="dash-pager-info">
        <i18n-t keypath="commons.table_showing" tag="span" scope="global">
          <template #from>
            <strong>{{ pageFrom }}</strong>
          </template>
          <template #to>
            <strong>{{ displayTo }}</strong>
          </template>
          <template #total>
            <strong>{{ displayTotal }}</strong>
          </template>
        </i18n-t>
        <select
          v-model.number="itemsPerPage"
          class="pager-size"
          :aria-label="$t('commons.rows_per_page')"
        >
          <option v-for="option in itemsPerPageOptions" :key="option" :value="option">
            {{ $t('commons.per_page', { option }) }}
          </option>
        </select>
      </div>
      <div class="pager-btns">
        <button class="pager-btn" :disabled="page <= 1" @click="page--">‹</button>
        <template v-for="(item, index) in pageItems" :key="`${index}-${item}`">
          <span v-if="item === '…'" class="pager-ellipsis">…</span>
          <button v-else class="pager-btn" :class="{ on: item === page }" @click="page = item">
            {{ item }}
          </button>
        </template>
        <button class="pager-btn" :disabled="page >= pageCount" @click="page++">›</button>
      </div>
    </div>

    <checkbox-dialog
      ref="downloadDialog"
      :title="$t('commons.download')"
      :items="checkboxDialogItems"
      loading-on-confirm
    />
  </v-card>
</template>

<style lang="scss" scoped>
/* EPFL design-system table — a light-DOM <table> (no per-row Vuetify components)
   so the body can re-render every frame during a crossfilter drag. Mirrors the
   handoff's .tbl styles. */
.stbl {
  border: 1px solid var(--border);
  border-radius: 0;
  background: var(--bg);
  /* Isolate the table's internal reflow/repaint from the rest of the page, so a
     filter-driven re-render here doesn't invalidate the chart strips below. */
  contain: layout;
}

.stbl-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
}
.stbl-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--title-card-size);
  font-weight: var(--title-card-weight);
  letter-spacing: var(--title-card-tracking);
}
.stbl-search :deep(.v-field) {
  border-radius: var(--radius);
  font-size: 14px;
}

/* Scroll viewport — sized to a *full* page (rows + the two header rows), capped
   at the 50vh scroll limit. Without a floor, filtering to fewer rows than the
   page size collapsed the body and shoved the charts below it. */
.stbl-scroll {
  min-height: min(calc(var(--stbl-rows, 5) * 38px + 96px), 50vh);
  max-height: 50vh;
  overflow-y: auto;
  overflow-x: auto;
}

.stbl-table {
  width: 100%;
  /* `separate` (not `collapse`) so the whole sticky <thead> keeps its borders
     while scrolling — collapsed borders detach from sticky headers in Chrome. */
  border-collapse: separate;
  border-spacing: 0;
  /* Fixed layout: columns take the weighted `<colgroup>` widths (summing to 100%),
     so the whole table fits with no horizontal overflow and headers/values
     ellipsis within their cell instead of forcing the column wide. */
  table-layout: fixed;
  font-size: 13px;
  font-feature-settings: 'tnum';
  background: var(--bg);
}

.stbl-col-select {
  width: 44px;
  text-align: center;
}

/* Sticky two-row header pinned as a single unit — no per-row offset, so the two
   header rows can never drift apart. */
.stbl-table thead {
  position: sticky;
  top: 0;
  z-index: 3;
}
.stbl-head-titles th {
  background: var(--bg-subtle);
}
.stbl-head-filters td {
  background: var(--bg);
}

/* Column header row */
.stbl-th {
  text-transform: uppercase;
  font-size: 11px;
  letter-spacing: 0.06em;
  font-weight: 700;
  color: var(--fg-muted);
  border-bottom: 1px solid var(--table-gridline-strong);
  cursor: pointer;
  user-select: none;
  padding: 6px 16px;
  text-align: start;
}
.stbl-th.text-end {
  text-align: end;
}
/* Title + sort icon on one line; the title truncates with an ellipsis while the
   icon stays visible (full title on hover via the cell's title attribute). */
.stbl-th-inner {
  display: flex;
  align-items: center;
  gap: 2px;
}
.stbl-th.text-end .stbl-th-inner {
  justify-content: flex-end;
}
.stbl-th-label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.stbl-th.is-sorted {
  color: var(--fg);
}
.stbl-sort {
  color: var(--epfl-red);
  flex: none;
}

/* Filter row (design-handoff bordered inputs) */
.stbl-head-filters td {
  border-bottom: 1px solid var(--table-gridline-strong);
  padding: 6px 6px;
}
.stbl-head-filters td .v-field {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg);
  font-size: 12px;
  padding-inline-start: 8px;
}
.stbl-head-filters td .v-field--focused {
  outline: 2px solid var(--epfl-red);
  outline-offset: -1px;
}
.stbl-head-filters td .v-field--variant-plain .v-field__input {
  padding-top: 4px;
  padding-bottom: 4px;
  min-height: 28px;
  font-size: 12px;
  opacity: 1;
}
.stbl-head-filters td .v-field--variant-plain .v-label {
  font-size: 12px;
}
.stbl-head-filters td .v-field__clearable,
.stbl-head-filters td .v-field__append-inner {
  padding-top: 2px;
}

/* Body rows. Height must stay in sync with ROW_HEIGHT in useVirtualRows.ts —
   the virtual window's scroll math assumes exactly this many px per row. */
.stbl-row {
  height: 38px;
}
.stbl-table tbody td {
  border-bottom: 1px solid var(--table-gridline);
  white-space: nowrap;
  padding: 0 16px;
}
/* Body cells clip to the column cap (select column exempt); only values longer
   than the cap show an ellipsis — short numbers never do. */
.stbl-table tbody td:not(.stbl-col-select) {
  overflow: hidden;
  text-overflow: ellipsis;
}
.stbl-table tbody td.text-end {
  text-align: end;
}
.stbl-row:hover {
  cursor: pointer;
  background: var(--bg-subtle);
}
/* Handoff .ed-table tr:hover .nm — the strong identifier cell reds on hover */
.stbl-row:hover .cell-strong {
  color: var(--epfl-red);
}
.stbl-row.is-selected {
  background: rgba(227, 7, 19, 0.05);
  box-shadow: inset 3px 0 0 var(--epfl-red);
}
.stbl-spacer td {
  padding: 0;
  border: none;
}

/* Selection checkboxes — EPFL red when checked */
.stbl-check {
  accent-color: var(--epfl-red);
  cursor: pointer;
  width: 16px;
  height: 16px;
}
.stbl-check:disabled {
  cursor: not-allowed;
  opacity: 0.4;
}

/* Cell treatments (design tbl) */
.cell-mono {
  font-family: var(--font-mono);
  font-size: 12px;
}
.cell-strong {
  font-weight: 600;
}
.tag {
  /* inherits the global .tag pill styling */
}

/* Loading indicator — a single EPFL-red segment with square ends marching along
   the header's bottom hairline, linear and looping. Scoped to the table head
   (height measured from the real <thead> in script) and absolutely positioned so
   it never affects layout; pointer-events stay off. */
.stbl-body {
  position: relative;
}
.stbl-loading {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 4;
  pointer-events: none;
  overflow: hidden;
  opacity: 0;
  transition: opacity 120ms ease;
}
.stbl-loading.is-loading {
  opacity: 1;
}
.stbl-loading::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: -26%;
  width: 26%;
  height: 2px;
  background: var(--epfl-red);
}
.stbl-loading.is-loading::after {
  animation: stbl-march 1s linear infinite;
}
@keyframes stbl-march {
  from {
    left: -26%;
  }
  to {
    left: 100%;
  }
}
/* No motion: hold a static full-width red hairline so the loading state still reads. */
@media (prefers-reduced-motion: reduce) {
  .stbl-loading.is-loading::after {
    animation: none;
    left: 0;
    width: 100%;
  }
}

:deep(input[type='number']) {
  width: 3em;
}

:deep(.v-list-item-title) {
  min-width: 200px;
}
</style>
