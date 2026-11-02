<script setup lang="ts" generic="M extends { id: string }">
import CheckboxDialog, { type CheckBoxDialogItem } from '@/components/commons/CheckboxDialog.vue'
import FilterInput from '@/components/commons/FilterInput.vue'
import TextSubscript, { stripSubSup } from '@/components/commons/TextSubscript.vue'
import { isBrushDragging } from '@/composables/interactionState'
import { DownloadType, type Column, type ColumnType } from '@/composables/table'
import { useFilterProfile } from '@/composables/useAutoFilters'
import { useColumnWidths, type MeasurableColumn } from '@/composables/useColumnWidths'
import { useVirtualRows } from '@/composables/useVirtualRows'
import i18n from '@/plugins/i18n'
import {
  displaySymbol,
  displayUnit,
  useDictionaryStore,
  type DictColumn
} from '@/stores/dictionary'
import { useNotificationStore } from '@/stores/notification'
import type { ColorScale } from '@/utils/categoryColors'
import { isStructuredFilterValue, shareCurrentUrl, type Searches, type Value } from '@/utils/common'
import { isUnverified } from '@/utils/curationStatus'
import type { FilterDescriptor } from '@/utils/filterProfile'
import { formatValue } from '@/utils/queryEngine'
import type { DatabaseId } from '@/utils/navigation'
import type { DataOptions } from '@/utils/vuetify'
import { booleanOptions } from '@/utils/vuetify'
import {
  mdiChevronDown,
  mdiClose,
  mdiDownload,
  mdiFilterRemoveOutline,
  mdiMagnify,
  mdiMenuDown,
  mdiMenuUp,
  mdiShare,
  mdiSortAscending,
  mdiSortDescending
} from '@mdi/js'
import { computed, nextTick, onMounted, onUnmounted, ref, shallowRef, useSlots, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'

interface TableHeader {
  type: ColumnType
  multiple?: boolean
  options?: string[]
  format?: (value: unknown) => string
  cellVariant?: 'mono' | 'tag' | 'strong'
  categoryColor?: boolean
  width?: number
  minWidth?: number
  // https://github.com/vuetifyjs/vuetify/blob/master/packages/vuetify/src/labs/VDataTable/types.ts
  key: string
  title: string
  /** Adaptive short label shown when space is tight; `isSymbol` marks a
   *  dictionary symbol whose case is semantic — rendered verbatim, not uppercased. */
  shortTitle?: { text: string; isSymbol: boolean }
  /** Dictionary unit shown in the header menu, when the title doesn't already carry it. */
  unit?: string
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
    /** Dictionary database id — enables adaptive short header labels derived
     *  from the data dictionary symbols when the long titles don't fit. */
    databaseId?: DatabaseId
    /** Category color scale per field (useDataset.colorFor) — paints the swatch of
     *  `categoryColor` columns with the same color the charts use for that value. */
    colorFor?: (field: string) => ColorScale
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
    liveItems: undefined,
    databaseId: undefined,
    colorFor: undefined
  }
)
const emit = defineEmits<{
  (e: 'click:row', value: M): void
  (e: 'download', items: M[], types: DownloadType[]): void
  (e: 'update:options', value?: DataOptions): void
  (e: 'update:search', value: string): void
  (e: 'update:searches', value: Searches): void
}>()

/** -1 = "All". `useTable` maps it to a 1000-row fetch, which exceeds every
 *  dataset (largest is ~370 rows), so it really does return everything. */
const ALL_ITEMS_PER_PAGE = -1
const itemsPerPageOptions = [25, 50, 100, ALL_ITEMS_PER_PAGE]
const vInputBind = {
  class: 'table-input',
  clearable: true,
  density: 'compact' as 'compact',
  hideDetails: true,
  singleLine: true,
  variant: 'underlined' as 'underlined'
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
// The data dictionary powers the adaptive short header labels; the store
// dedupes, so this kicks at most one fetch per session. Until it resolves
// (or without a databaseId) headers simply never shorten.
const dictionaryStore = useDictionaryStore()
if (props.databaseId) void dictionaryStore.fetch()

const downloadDialog = ref<InstanceType<typeof CheckboxDialog>>()
const selectedItemsIds = ref<string[]>([])
// shallowRef, and not just for performance: a deep ref would unwrap the generic
// M (UnwrapRefSimple<M>) and break the typing of everything touching it.
const selectedItems = shallowRef<M[]>([])
const page = ref<number>(1)
/** On an ultrawide screen the table owns the full height of its column, so the
 *  default page is the whole dataset rather than the first 50 — you scroll the
 *  same table either way, minus the paging. Read once at setup: flipping this on
 *  resize would silently discard a page size the user had chosen. Matches the
 *  2100px split breakpoint in app.css. */
const itemsPerPage = ref<number>(
  window.matchMedia('(min-width: 2100px)').matches ? ALL_ITEMS_PER_PAGE : 50
)
const sortBy = ref<{ key: string; order: 'asc' | 'desc' }>()
// Which column's header menu (sort + filter popover) is open, keyed by column.
// Sort actions close it; filter edits keep it open.
const openMenuKey = ref<string>()

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

// Size the loading shimmer to the table head only, and let the scroll viewport
// subtract the head from its height cap. The header height is stable per dashboard
// but varies between them, so measure the real head band — including its bottom
// hairline, which is the line the shimmer marches along — and track it via
// ResizeObserver, exposing it as `--stbl-head-h`.
const scrollEl = ref<HTMLElement>()
const headEl = ref<HTMLElement>()
const hscrollEl = ref<HTMLElement>()
const headHeight = ref<string>('44px')
// Width of the horizontal scroll wrapper — the space the columns have to fill.
// Read from `hscrollEl` (not `headEl`, which is content-sized and can be wider
// than the viewport once the table overflows). Fractional, so the distributed
// column widths add up to the real content box, not a rounded one.
const containerWidth = ref<number>(0)
let headObserver: ResizeObserver | undefined
function measureHead(): void {
  if (headEl.value) headHeight.value = `${headEl.value.offsetHeight}px`
  if (hscrollEl.value) containerWidth.value = hscrollEl.value.getBoundingClientRect().width
}

/* ---- Overlay scrollbar ----------------------------------------------------
 * The native scrollbar is hidden (see `.stbl-scroll`) and a thumb is drawn over
 * the rows: a native one takes its width out of the scrollport, which either
 * shifts every column when the rows outgrow the panel or (gutter reserved)
 * leaves dead space when they don't. Overlaying costs neither — the content box
 * never changes width. Wheel/trackpad/keyboard/touch scrolling are untouched;
 * only the drag has to be implemented. */
const THUMB_MIN_HEIGHT = 24
const thumbVisible = ref<boolean>(false)
const thumbHeight = ref<number>(0)
const thumbTop = ref<number>(0)
function updateThumb(): void {
  const el = scrollEl.value
  if (!el) return
  const track = el.clientHeight
  const overflow = el.scrollHeight - track
  // Sub-pixel overflow is layout rounding, not content — don't flash a thumb for it.
  thumbVisible.value = overflow > 1
  if (!thumbVisible.value) return
  thumbHeight.value = Math.max(THUMB_MIN_HEIGHT, (track / el.scrollHeight) * track)
  thumbTop.value = (el.scrollTop / overflow) * (track - thumbHeight.value)
}

function onThumbPointerDown(event: PointerEvent): void {
  const el = scrollEl.value
  if (!el) return
  const startY = event.clientY
  const startScroll = el.scrollTop
  const travel = el.clientHeight - thumbHeight.value
  const overflow = el.scrollHeight - el.clientHeight
  if (travel <= 0 || overflow <= 0) return
  const thumb = event.currentTarget as HTMLElement
  const onMove = (moveEvent: PointerEvent): void => {
    el.scrollTop = startScroll + ((moveEvent.clientY - startY) / travel) * overflow
  }
  const onUp = (): void => {
    thumb.removeEventListener('pointermove', onMove)
    thumb.removeEventListener('pointerup', onUp)
    thumb.removeEventListener('pointercancel', onUp)
  }
  // Pointer capture keeps the drag alive when the cursor leaves the 8px thumb,
  // which is most of any real drag.
  thumb.setPointerCapture(event.pointerId)
  thumb.addEventListener('pointermove', onMove)
  thumb.addEventListener('pointerup', onUp)
  thumb.addEventListener('pointercancel', onUp)
  event.preventDefault()
}

// Recompute after any render that changes how much there is to scroll. The
// crossing into (or out of) scrollable happens with the viewport's own box
// unchanged, so a ResizeObserver on it never sees it.
watch(displayItems, async () => {
  await nextTick()
  updateThumb()
})

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
  updateThumb()
  if ('ResizeObserver' in window) {
    headObserver = new ResizeObserver(() => {
      measureHead()
      updateThumb()
    })
    // Covers the container actually changing size — window resize, the ultrawide
    // split handing the table a column. Content-driven changes are caught by the
    // watch above, not here.
    if (headEl.value) headObserver.observe(headEl.value)
    if (scrollEl.value) headObserver.observe(scrollEl.value)
    if (hscrollEl.value) headObserver.observe(hscrollEl.value)
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
// Height floor for the scroll viewport, in rows. Driven by the unfiltered
// dataset size, which is constant per page, so filtering never resizes the
// panel and shifts the charts below it. Small datasets still get a compact
// panel instead of being pinned at the 50vh cap.
const heightRows = computed<number>(() => Math.max(3, props.totalCount ?? totalRows.value))
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

// Content-measured column widths (see useColumnWidths): each column is sized to
// its widest header/value; leftover space goes to the text columns, and when the
// mins don't fit the table grows past the container into the horizontal scroll
// wrapper. Measured over the COMMITTED page only — live crossfilter drag rows
// are never measured, and the ratchet keeps widths still during a drag.
const measurableColumns = computed<MeasurableColumn[]>(() =>
  tableHeaders.value.map((header) => ({
    key: header.key,
    title: stripSubSup(header.title),
    shortTitle: header.shortTitle
      ? { text: stripSubSup(header.shortTitle.text), isSymbol: header.shortTitle.isSymbol }
      : undefined,
    type: header.type,
    format: header.format,
    cellVariant: header.cellVariant,
    categoryColor: header.categoryColor,
    width: header.width,
    minWidth: header.minWidth
  }))
)
const { columnWidths, tableWidth, useShortTitles } = useColumnWidths(
  measurableColumns,
  computed(() => props.items as unknown as readonly Record<string, unknown>[]),
  containerWidth
)

// "All" (-1) would make the pager math go negative, so resolve it to the full
// filtered count first — every page computation below rides this, not the raw
// itemsPerPage.
const effectivePageSize = computed<number>(() =>
  itemsPerPage.value === ALL_ITEMS_PER_PAGE
    ? Math.max(1, props.totalFilteredCount)
    : itemsPerPage.value
)
const pageCount = computed<number>(() =>
  Math.max(1, Math.ceil(props.totalFilteredCount / effectivePageSize.value))
)
const pageFrom = computed<number>(() =>
  props.totalFilteredCount === 0 ? 0 : (page.value - 1) * effectivePageSize.value + 1
)
const pageTo = computed<number>(() =>
  Math.min(page.value * effectivePageSize.value, props.totalFilteredCount)
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

// Sort / page / size are owned here and pushed to the parent via `update:options`,
// exactly as `v-data-table-server` used to — `useTable` re-fetches from them.
function emitOptions(): void {
  emit('update:options', {
    sortBy: sortBy.value ? [sortBy.value] : [],
    page: page.value,
    itemsPerPage: itemsPerPage.value
  })
}

// The menu opens on hover, so a pointer that drifts off while the user is typing
// in the filter input must not close it. Track focus inside the popover and veto
// the hover-out close for as long as it's there.
const menuHasFocus = ref(false)
function toggleMenu(header: TableHeader, open: boolean): void {
  // A histogram drag also wanders off the popover; keep it open until pointer-up.
  if (!open && (menuHasFocus.value || isBrushDragging.value)) return
  openMenuKey.value = open ? header.key : undefined
}

// The dashboard's profiled filters (see useAutoFilters) give the menu the same
// inputs as the rail — a value list for categories, a histogram with bounds for
// numbers — where the column's declared type would only offer a text box.
const filterProfile = useFilterProfile(() => props.databaseId)
const filterByKey = computed(
  () => new Map(filterProfile.value.map((descriptor) => [descriptor.key, descriptor]))
)
const slots = useSlots()
/**
 * The profiled filter to render in a column's menu, or undefined to fall back to
 * the declared-type inputs: free text keeps its instant native input, and a
 * column with a custom select item (the connection-type pictures) keeps its
 * select.
 */
function richFilterFor(header: TableHeader): FilterDescriptor | undefined {
  if (slots[`header-select-item.${header.key}`]) return undefined
  const descriptor = filterByKey.value.get(header.key)
  if (!descriptor) return undefined
  switch (descriptor.kind) {
    case 'categorical':
    case 'boolean':
      return descriptor.options ? descriptor : undefined
    case 'numeric':
      return descriptor.binEdges ? descriptor : undefined
    case 'date':
      return descriptor.dateMin && descriptor.dateMax ? descriptor : undefined
    default:
      return undefined
  }
}
// The rail's inputs clear with `undefined`; the searches object holds no key for
// a cleared filter (see useDashboard.changeSearches), so drop it rather than
// storing an empty value the query builder would have to skip.
function setColumnSearch(header: TableHeader, value?: Value): void {
  if (value === undefined || value === '') delete columnSearches.value[header.key]
  else columnSearches.value[header.key] = value
}
// A rich column offers both inputs — the rail's (value list / histogram) and a
// typed box for one exact number or a text fragment. They write the same key,
// so whichever holds the value owns it and the other is greyed out until it is
// cleared. The grammar tells them apart: the rail's inputs emit `=value`,
// arrays and `lo<<hi`; the typed box stores bare text.
function richValueFor(header: TableHeader): Value | undefined {
  const value = columnSearches.value[header.key]
  return isStructuredFilterValue(value) ? value : undefined
}
function typedValueFor(header: TableHeader): string | undefined {
  const value = columnSearches.value[header.key]
  if (isStructuredFilterValue(value) || !hasColumnFilter(header)) return undefined
  return String(value)
}
/** Booleans and dates gain nothing from a text box; numbers and categories do. */
function hasTypedInput(filter: FilterDescriptor): boolean {
  return filter.kind === 'numeric' || filter.kind === 'categorical'
}
function onMenuFocusOut(event: FocusEvent): void {
  const root = event.currentTarget as HTMLElement
  const next = event.relatedTarget as Node | null
  // focusout also fires when moving between elements *inside* the popover.
  if (!next || !root.contains(next)) menuHasFocus.value = false
}
function closeMenu(): void {
  menuHasFocus.value = false
  openMenuKey.value = undefined
}

// Sort is chosen explicitly from the per-column header menu, so both directions
// are always reachable in one action and the menu closes once a direction is
// picked. Clicking the header itself cycles asc → desc → unsorted instead.
function setSort(header: TableHeader, order: 'asc' | 'desc'): void {
  sortBy.value = { key: header.key, order }
  closeMenu()
}
// The header menu is hover-only (`open-on-hover` without `open-on-click`), so
// this is the activator's sole click action — the open menu stays put and its
// sort rows just reflect the new state.
function cycleSort(header: TableHeader): void {
  if (sortBy.value?.key !== header.key) {
    sortBy.value = { key: header.key, order: 'asc' }
  } else if (sortBy.value.order === 'asc') {
    sortBy.value = { key: header.key, order: 'desc' }
  } else {
    sortBy.value = undefined
  }
}
// Return to the unsorted (natural) order — emitOptions sends an empty sortBy,
// which useTable maps to empty sort params.
function clearSort(): void {
  sortBy.value = undefined
  closeMenu()
}

// A column carries an active filter when its search value is a non-empty string
// or a non-empty multi-select array — drives the dot marker on the header.
function hasColumnFilter(header: TableHeader): boolean {
  const value = columnSearches.value[header.key]
  if (Array.isArray(value)) return value.length > 0
  return value !== undefined && value !== null && value !== ''
}

function isRowSelected(item: M): boolean {
  return selectedItemsIds.value.includes(item.id)
}
function toggleRow(item: M): void {
  if (isRowSelected(item)) {
    selectedItemsIds.value = selectedItemsIds.value.filter((id) => id !== item.id)
  } else {
    selectedItemsIds.value = [...selectedItemsIds.value, item.id]
  }
}
// Header checkbox: select every row of the page, or clear them if all are selected.
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
  for (const item of displayItems.value) set.add(item.id)
  selectedItemsIds.value = [...set]
}

function cellText(header: TableHeader, item: M): string {
  const value = (item as Record<string, unknown>)[header.key]
  if (value === null || value === undefined) return ''
  return header.format ? header.format(value) : String(value)
}

// Keyed by the same string the aggregators group on (formatValue), so a boolean
// or numeric category resolves to the color its chart tile/series wears.
function categoryColor(header: TableHeader, item: M): string | undefined {
  if (!header.categoryColor || !props.colorFor) return undefined
  const value = (item as Record<string, unknown>)[header.key]
  if (value === null || value === undefined) return undefined
  return props.colorFor(header.key)(formatValue(value))
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

// Adaptive short label candidate, by precedence: an explicit `shortTitle`
// string, then the `{titleKey}_short` locale key (contextual wording, e.g.
// "Connection Type" → "Type"), then the dictionary symbol (+ unit). Identity
// columns opt out through the data — their symbol is the `-` sentinel.
function shortCandidateFor(
  column: Column,
  titleKey: string | undefined,
  dict: DictColumn | undefined
): TableHeader['shortTitle'] {
  if (typeof column.shortTitle === 'string') return { text: column.shortTitle, isSymbol: false }
  const shortKey = titleKey && `${titleKey}_short`
  if (shortKey && i18n.global.te(shortKey)) {
    return { text: i18n.global.t(shortKey).toString(), isSymbol: false }
  }
  const symbol = dict && displaySymbol(dict)
  if (!symbol) return undefined
  const unit = displayUnit(dict!)
  return { text: unit ? `${symbol} [${unit}]` : symbol, isSymbol: true }
}

function shortLabelFor(
  column: Column,
  titleKey: string | undefined,
  title: string,
  dict: DictColumn | undefined
): TableHeader['shortTitle'] {
  if (column.shortTitle === false) return undefined
  const short = shortCandidateFor(column, titleKey, dict)
  // A "short" label that isn't shorter would widen the column under space pressure.
  return short && stripSubSup(short.text).length < stripSubSup(title).length ? short : undefined
}

// Dictionary unit for the header-menu title line — omitted when the title
// already carries it (many locale titles bake in "[mm]" etc.).
function unitFor(dict: DictColumn | undefined, title: string): string | undefined {
  const unit = dict && displayUnit(dict)
  return unit && !title.includes(`[${unit}]`) ? unit : undefined
}

function getTableHeader(column: Column): TableHeader {
  // Locale key behind the title: explicit `titleKey`, else the prefix
  // convention — absent when the title is a literal string.
  const titleKey =
    column.titleKey ?? (column.title === undefined ? props.prefix + column.value : undefined)
  const title = column.title ?? i18n.global.t(titleKey as string).toString()
  const dict = props.databaseId
    ? dictionaryStore.columnFor(props.databaseId, column.value)
    : undefined
  return {
    key: column.value,
    title,
    shortTitle: shortLabelFor(column, titleKey, title, dict),
    unit: unitFor(dict, title),
    type: column.type,
    format: column.format,
    cellVariant: column.cellVariant,
    categoryColor: column.categoryColor,
    width: column.width,
    minWidth: column.minWidth,
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
  <v-card
    class="stbl"
    flat
    :style="{ '--stbl-rows': String(heightRows), '--stbl-head-h': headHeight }"
  >
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
      <!-- One shared horizontal scroller around BOTH tables: when the measured
           column mins outgrow the viewport, head and body overflow together and
           stay aligned with zero scroll-sync JS. Vertical scrolling stays on
           `.stbl-scroll` alone. An open header menu is anchored to a fixed
           overlay, so it must close when its activator scrolls away sideways. -->
      <div ref="hscrollEl" class="stbl-hscroll" @scroll.passive="closeMenu">
        <!-- The header is its own table *outside* the vertical scroll viewport,
             so it holds still without `sticky` and the scrollbar tracks the data
             rows only. The two tables stay column-aligned because they share the
             `<colgroup>` widths and the overlay scrollbar takes no width from
             either. -->
        <div ref="headEl" class="stbl-head">
          <table class="stbl-table" :style="{ width: tableWidth }">
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
                  :class="{
                    'text-end': header.align === 'end',
                    'is-sorted': sortBy?.key === header.key
                  }"
                >
                  <!-- Per-column menu: sort direction + this column's filter, opened
                     from the header itself so the header stays a single row. -->
                  <v-menu
                    :model-value="openMenuKey === header.key"
                    :close-on-content-click="false"
                    :transition="false"
                    open-on-hover
                    :open-delay="90"
                    :close-delay="220"
                    :offset="0"
                    location="bottom start"
                    @update:model-value="toggleMenu(header, $event)"
                  >
                    <template #activator="{ props: activatorProps }">
                      <button
                        v-bind="activatorProps"
                        type="button"
                        class="stbl-th-inner"
                        :title="stripSubSup(header.title)"
                        :aria-label="`${stripSubSup(header.title)} – ${$t(
                          'commons.column_options'
                        )}`"
                        @click="cycleSort(header)"
                      >
                        <!-- Tooltip/aria keep the long title; only the visible
                             label swaps to the short one when space is tight.
                             Word shorts uppercase like any header; only symbol
                             shorts keep their (semantic) case. -->
                        <span
                          class="stbl-th-label"
                          :class="{ 'is-symbol': useShortTitles && header.shortTitle?.isSymbol }"
                        >
                          <text-subscript
                            :text="
                              useShortTitles && header.shortTitle
                                ? header.shortTitle.text
                                : header.title
                            "
                          />
                        </span>
                        <v-icon
                          v-if="sortBy?.key === header.key"
                          class="stbl-sort"
                          size="14"
                          :icon="sortBy?.order === 'asc' ? mdiMenuUp : mdiMenuDown"
                        />
                        <span v-if="hasColumnFilter(header)" class="stbl-th-dot" />
                        <v-icon class="stbl-th-caret" size="12" :icon="mdiChevronDown" />
                      </button>
                    </template>

                    <div
                      class="stbl-menu"
                      @focusin="menuHasFocus = true"
                      @focusout="onMenuFocusOut"
                    >
                      <button
                        type="button"
                        class="stbl-menu-item"
                        :class="{ on: sortBy?.key === header.key && sortBy?.order === 'asc' }"
                        @click="setSort(header, 'asc')"
                      >
                        <v-icon size="16" :icon="mdiSortAscending" />
                        {{ $t('commons.sort_asc') }}
                      </button>
                      <button
                        type="button"
                        class="stbl-menu-item"
                        :class="{ on: sortBy?.key === header.key && sortBy?.order === 'desc' }"
                        @click="setSort(header, 'desc')"
                      >
                        <v-icon size="16" :icon="mdiSortDescending" />
                        {{ $t('commons.sort_desc') }}
                      </button>
                      <button
                        v-if="sortBy?.key === header.key"
                        type="button"
                        class="stbl-menu-item"
                        @click="clearSort()"
                      >
                        <v-icon size="16" :icon="mdiClose" />
                        {{ $t('commons.clear_sort') }}
                      </button>
                      <div class="stbl-menu-filter" :class="{ 'is-rich': !!richFilterFor(header) }">
                        <!-- The rail's input for this column (value list, histogram
                             with its bounds below, date range). Mounted only while
                             this menu is open: the ECharts brush is the one thing
                             here too heavy to keep around for every column. -->
                        <template v-if="richFilterFor(header)">
                          <div
                            class="stbl-menu-rich"
                            :class="{ 'is-off': typedValueFor(header) !== undefined }"
                            :aria-disabled="typedValueFor(header) !== undefined"
                          >
                            <filter-input
                              v-if="openMenuKey === header.key"
                              fields="below"
                              :filter="richFilterFor(header)!"
                              :meta="false"
                              :value="richValueFor(header)"
                              @update="setColumnSearch(header, $event)"
                            />
                          </div>
                          <!-- One exact number, or a text fragment, typed instead
                               of brushed or ticked. -->
                          <input
                            v-if="hasTypedInput(richFilterFor(header)!)"
                            class="stbl-menu-input stbl-menu-typed"
                            :type="richFilterFor(header)!.kind === 'numeric' ? 'number' : 'search'"
                            :disabled="richValueFor(header) !== undefined"
                            :value="typedValueFor(header) ?? ''"
                            :placeholder="
                              richFilterFor(header)!.kind === 'numeric'
                                ? $t('commons.exact_value')
                                : $t('commons.contains_text')
                            "
                            @input="
                              setColumnSearch(header, ($event.target as HTMLInputElement).value)
                            "
                          />
                        </template>
                        <v-select
                          v-else-if="header.options"
                          v-bind="vInputBind"
                          :model-value="(columnSearches[header.key] as string)"
                          :label="$t('commons.filter')"
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
                        <!-- Native inputs for the common text/number columns: a
                           Vuetify field mounts on first hover of every column and
                           that cost is what reads as hover lag. Matches the
                           light-DOM approach used by the body and the pager. -->
                        <input
                          v-else-if="header.type === 'text'"
                          v-model="columnSearches[header.key]"
                          class="stbl-menu-input"
                          type="search"
                          :placeholder="$t('commons.filter')"
                        />
                        <input
                          v-else-if="header.type === 'number'"
                          v-model="columnSearches[header.key]"
                          class="stbl-menu-input"
                          type="number"
                          :placeholder="$t('commons.filter')"
                        />
                        <v-select
                          v-else-if="header.type === 'boolean'"
                          v-bind="vInputBind"
                          v-model="columnSearches[header.key]"
                          :label="$t('commons.filter')"
                          :items="booleanOptions"
                        />
                      </div>
                      <!-- Drops this column's filter, whichever input set it.
                           Stays open, like the filter edits, so the inputs are
                           seen coming back. -->
                      <button
                        v-if="hasColumnFilter(header)"
                        type="button"
                        class="stbl-menu-item"
                        @click="setColumnSearch(header, undefined)"
                      >
                        <v-icon size="16" :icon="mdiFilterRemoveOutline" />
                        {{ $t('commons.clear_filter') }}
                      </button>
                      <div class="stbl-menu-sep" />
                      <!-- Full column title (+ unit) as a caption — the visible
                           header may be ellipsised or swapped to its short label. -->
                      <div class="stbl-menu-title">
                        <text-subscript :text="header.title" />
                        <span v-if="header.unit" class="stbl-menu-unit">[{{ header.unit }}]</span>
                      </div>
                    </div>
                  </v-menu>
                </th>
              </tr>
            </thead>
          </table>
        </div>

        <div ref="scrollEl" class="stbl-scroll" @scroll="updateThumb">
          <table class="stbl-table" :style="{ width: tableWidth }">
            <colgroup>
              <col class="stbl-col-select" />
              <col
                v-for="(header, index) in tableHeaders"
                :key="header.key"
                :style="{ width: columnWidths[index] }"
              />
            </colgroup>
            <tbody>
              <tr
                v-if="rowWindow.padTop"
                class="stbl-spacer"
                :style="{ height: `${rowWindow.padTop}px` }"
              >
                <td :colspan="tableHeaders.length + 1"></td>
              </tr>
              <tr
                v-for="(item, index) in visibleRows"
                :key="item.id"
                class="stbl-row"
                :class="{
                  'is-selected': isRowSelected(item),
                  'is-stripe': (rowWindow.startIndex + index) % 2 === 1
                }"
                @click="rowClick(item)"
              >
                <td
                  class="stbl-col-select"
                  :class="{ 'is-unverified': isUnverified(item) }"
                  :title="isUnverified(item) ? t('commons.unverified.row_title') : undefined"
                  @click.stop
                >
                  <input
                    type="checkbox"
                    class="stbl-check"
                    :checked="isRowSelected(item)"
                    @change="toggleRow(item)"
                  />
                  <span v-if="isUnverified(item)" class="stbl-sr">{{
                    t('commons.unverified.tag')
                  }}</span>
                </td>
                <td
                  v-for="header in tableHeaders"
                  :key="header.key"
                  :title="cellText(header, item)"
                  :class="{ 'text-end': header.align === 'end' }"
                >
                  <span
                    v-if="header.categoryColor && cellText(header, item)"
                    class="tag cell-category"
                    :style="{ '--category-color': categoryColor(header, item) }"
                    >{{ cellText(header, item) }}</span
                  >
                  <span
                    v-else-if="header.cellVariant === 'tag' && cellText(header, item)"
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
      </div>
      <!-- Overlay scrollbar, drawn over the rows so they keep the full width of the
           panel whether or not there is anything to scroll. -->
      <div
        v-if="thumbVisible"
        class="stbl-sbar-thumb"
        :style="{ height: `${thumbHeight}px`, transform: `translateY(${thumbTop}px)` }"
        aria-hidden="true"
        @pointerdown="onThumbPointerDown"
      />

      <div class="stbl-loading" :class="{ 'is-loading': showLoading }" aria-hidden="true" />
    </div>

    <!-- Design-handoff pager -->
    <div class="dash-pager">
      <div class="dash-pager-actions">
        <button
          class="btn btn-secondary btn-sm"
          :disabled="selectedItems.length === 0"
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
            {{
              option === ALL_ITEMS_PER_PAGE
                ? $t('commons.per_page_all')
                : $t('commons.per_page', { option })
            }}
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
  /* Overlay-thumb geometry, shared by the thumb itself and by the right-hand
     padding that keeps the last column clear of it. */
  --stbl-sbar-w: 8px;
  --stbl-sbar-inset: 3px;
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

/* Horizontal scroll wrapper around BOTH tables. On wide screens the columns sum
   to the container and this never engages; when the measured column mins don't
   fit, the tables (explicit px width) overflow it together — one scroller, so
   head and body can't desync. A native bottom scrollbar costs no column width
   (unlike the vertical one, overlaid for that reason) and only appears when
   there is actually something to scroll. */
.stbl-hscroll {
  overflow-x: auto;
  overscroll-behavior-x: contain;
}
@media (pointer: fine) {
  .stbl-hscroll {
    scrollbar-width: thin;
    scrollbar-color: var(--border-strong) transparent;
  }
  .stbl-hscroll::-webkit-scrollbar {
    height: 8px;
  }
  .stbl-hscroll::-webkit-scrollbar-thumb {
    background: var(--border-strong);
  }
}

/* Head band. Painted by the container rather than the cells so the grey and its
   hairline run unbroken under the whole head — select column included, which has
   no `.stbl-th` to carry a border of its own. `fit-content` (resolved from the
   table's explicit px width) keeps the band spanning the full scrolled width
   instead of clipping at the viewport. */
.stbl-head {
  width: fit-content;
  min-width: 100%;
  background: var(--bg-subtle);
  border-bottom: 1px solid var(--table-gridline-strong);
}
/* Plain full width: with the body's scrollbar overlaid rather than in-flow, the two
   tables always have the same space to fill. Transparent so the band above shows
   through instead of `--bg`. */
.stbl-head .stbl-table {
  background: transparent;
}

/* Scroll viewport — sized to a *full* page of rows, capped so the panel as a whole
   (head + rows) still fits the 50vh scroll limit. Without a floor, filtering to
   fewer rows than the page size collapsed the body and shoved the charts below it. */
.stbl-scroll {
  min-height: min(calc(var(--stbl-rows, 5) * 38px), calc(50vh - var(--stbl-head-h, 44px)));
  max-height: calc(50vh - var(--stbl-head-h, 44px));
  /* Vertical only. Horizontal overflow belongs to `.stbl-hscroll` — this box is
     sized to its table (`fit-content`, from the table's explicit px width) so
     the rows never overflow it sideways and its own overflow-x never engages. */
  width: fit-content;
  min-width: 100%;
  overflow-y: auto;
  /* Native scrollbar hidden — `.stbl-sbar-thumb` draws over the rows instead, so the
     scrollport keeps its full width and nothing shifts when the rows outgrow the
     panel. Scrolling itself (wheel, trackpad, keyboard, touch) is untouched. */
  scrollbar-width: none;
}
.stbl-scroll::-webkit-scrollbar {
  width: 0;
  height: 0;
}

/* Overlay thumb. Positioned against `.stbl-body`, offset by the head so it tracks
   the rows only — same span as the viewport it represents. */
.stbl-sbar-thumb {
  position: absolute;
  top: var(--stbl-head-h, 44px);
  right: var(--stbl-sbar-inset);
  width: var(--stbl-sbar-w);
  z-index: 3;
  background: var(--border-strong);
  opacity: 0.55;
  cursor: default;
  transition: opacity 120ms ease;
}
.stbl-sbar-thumb:hover {
  opacity: 0.85;
}
/* Coarse pointers get the platform's own overlay scrollbar, which takes no width
   either — ours would just be a second one that can't be flicked. */
@media (pointer: coarse) {
  .stbl-sbar-thumb {
    display: none;
  }
}

/* On the ultrawide database split the charts have their own column, so the 50vh
   cap — which only existed to stop the table from pushing them off-screen — has
   nothing left to protect, and the table fills the column instead.

   The height is passed down the flex chain rather than reserved as a fixed
   offset: the page header, toolbar, the CONDITIONAL active-filter bar and the
   pager all take their natural height first and the scroll viewport absorbs
   what's left. A fixed offset hid the pager as soon as a filter chip appeared
   and changed the header's height. */
@media (min-width: 2100px) {
  .dash-col-main .stbl {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
  }
  .dash-col-main .stbl-body {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
  }
  /* The horizontal scroll wrapper sits in this flex chain too — without passing
     the height through it, the scroll viewport would collapse to content. */
  .dash-col-main .stbl-hscroll {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
  }
  .dash-col-main .stbl-scroll {
    flex: 1;
    min-height: 0;
    max-height: none;
  }
}

.stbl-table {
  /* Fallback only — the template binds an explicit px width computed with the
     column measurement, container-fit when everything fits and wider when the
     column mins overflow into the horizontal scroller. */
  width: 100%;
  /* `separate` (not `collapse`) so the whole sticky <thead> keeps its borders
     while scrolling — collapsed borders detach from sticky headers in Chrome. */
  border-collapse: separate;
  border-spacing: 0;
  /* Fixed layout: columns take exactly the measured `<colgroup>` px widths —
     content never forces a column wide; values longer than their measured cap
     ellipsis within the cell. */
  table-layout: fixed;
  font-size: 13px;
  font-feature-settings: 'tnum';
  background: var(--bg);
}

.stbl-col-select {
  width: 44px;
  text-align: center;
}
/* The select column is a fixed 44px gutter, not a text cell: drop the 16px side
   padding (which left a 12px box for a 15px control, pushing it off-centre) and
   let the cell centre its block child on both axes. */
.stbl-table th.stbl-col-select,
.stbl-table tbody td.stbl-col-select {
  padding: 0;
  vertical-align: middle;
}

/* Column header row */
.stbl-th {
  text-transform: uppercase;
  font-size: 11px;
  letter-spacing: 0.06em;
  font-weight: 700;
  color: var(--fg-muted);
  user-select: none;
  padding: 0;
  text-align: start;
}
/* The whole header cell is the menu activator — a real <button> so the column
   menu is keyboard-reachable and announced as a control. */
.stbl-th-inner {
  display: flex;
  align-items: center;
  gap: 2px;
  width: 100%;
  /* Vertical padding sets the head band's height — the select column's checkbox
     centres against whatever this row resolves to. */
  padding: 12px 16px;
  border: 0;
  background: none;
  cursor: pointer;
  font: inherit;
  color: inherit;
  text-transform: inherit;
  letter-spacing: inherit;
  text-align: inherit;
}
.stbl-th-inner:hover {
  background: var(--bg);
}
.stbl-th-inner:focus-visible {
  outline: 2px solid var(--epfl-red);
  outline-offset: -2px;
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
/* Symbol labels keep their case — it's semantic (t ≠ T) — while inheriting the
   header letter-spacing the width measurer compensates for. */
.stbl-th-label.is-symbol {
  text-transform: none;
}
.stbl-th.is-sorted {
  color: var(--fg);
}
.stbl-sort {
  color: var(--epfl-red);
  flex: none;
}
/* Marks a column whose filter is set — the filter input now lives behind the
   menu, so this is what keeps an active filter visible at a glance. */
.stbl-th-dot {
  flex: none;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--epfl-red);
}
/* Menu affordance: muted until the header is hovered/focused. */
.stbl-th-caret {
  flex: none;
  margin-inline-start: auto;
  opacity: 0.35;
}
.stbl-th.text-end .stbl-th-caret {
  margin-inline-start: 2px;
}
.stbl-th-inner:hover .stbl-th-caret,
.stbl-th-inner:focus-visible .stbl-th-caret {
  opacity: 1;
}

/* Per-column header menu (sort + filter) */
.stbl-menu {
  min-width: 220px;
  /* Never wider than a phone screen, minus a 16px gutter on each side. */
  max-width: calc(100vw - 32px);
  padding: 4px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: 0 6px 24px rgb(0 0 0 / 12%);
}
.stbl-menu-title {
  padding: 5px 10px 7px;
  font-size: 12px;
  font-weight: 600;
  color: var(--fg);
  /* Long titles wrap rather than widening the popover past its min-width. */
  overflow-wrap: break-word;
}
.stbl-menu-unit {
  margin-left: 4px;
  font-weight: 400;
  color: var(--fg-muted);
}
.stbl-menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 7px 10px;
  border: 0;
  border-radius: var(--radius);
  background: none;
  cursor: pointer;
  font-size: 13px;
  color: var(--fg);
  text-align: start;
}
.stbl-menu-item:hover {
  background: var(--bg-subtle);
}
.stbl-menu-item.on {
  color: var(--epfl-red);
  font-weight: 600;
}
.stbl-menu-sep {
  height: 1px;
  margin: 4px 0;
  background: var(--border);
}
.stbl-menu-filter {
  padding: 2px 10px 6px;
}
/* The rail's inputs need room for a histogram or a value list with counts;
   the popover is otherwise sized to its sort rows. */
.stbl-menu-filter.is-rich {
  width: 280px;
  max-width: 100%;
  padding-top: 6px;
}
.stbl-menu-filter.is-rich .afr-options {
  margin: 0 -4px;
}
/* Whichever of the two inputs holds the filter owns it: the other fades and
   stops taking the pointer until the value is cleared. */
.stbl-menu-rich.is-off {
  opacity: 0.4;
  pointer-events: none;
}
.stbl-menu-typed {
  margin-top: 10px;
}
.stbl-menu-typed:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.stbl-menu-input {
  width: 100%;
  padding: 6px 8px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg);
  font: inherit;
  font-size: 13px;
  color: var(--fg);
}
.stbl-menu-input:focus {
  outline: 2px solid var(--epfl-red);
  outline-offset: -1px;
}

/* Body rows. Height must stay in sync with ROW_HEIGHT in useVirtualRows.ts —
   the virtual window's scroll math assumes exactly this many px per row. */
.stbl-row {
  height: 38px;
}
/* Zebra striping. Parity is computed from the absolute row index in the template
   (not :nth-child) because the body is virtualized — spacer rows and a shifting
   render window make DOM position unreliable. Declared before :hover/.is-selected
   so those states still win. */
.stbl-row.is-stripe {
  background: var(--table-row-stripe);
}
.stbl-table tbody td {
  border-bottom: 1px solid var(--table-gridline);
  white-space: nowrap;
  padding: 0 16px;
}
/* The last column is the one the thumb sits over, and it is usually the right-aligned
   numeric one, so its values would otherwise run right up against the thumb. Clear
   its width, then keep a 12px gutter. Applied unconditionally, not only while the
   thumb is showing — the whole point of overlaying it is that nothing moves when the
   rows outgrow the panel. */
.stbl-th:last-child .stbl-th-inner,
.stbl-table tbody td:last-child {
  padding-right: calc(var(--stbl-sbar-inset) + var(--stbl-sbar-w) + 12px);
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
/* Unverified row (#253): an orange rule on the left edge, in the fixed select
   gutter. Not a tag in the first cell: the widths are measured from the text
   alone, so a tag would push the id out of its column. A selected row keeps
   its red rule, drawn on the row. */
.stbl-row:not(.is-selected) td.stbl-col-select.is-unverified {
  box-shadow: inset 3px 0 0 var(--warning);
}
.stbl-sr {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}

/* Selection checkboxes — EPFL red when checked */
/* Square by construction: `accent-color` alone keeps the UA's rounded box, so the
   control is drawn from scratch — square corners, hairline border, EPFL red when
   set. Grid (a block-level box) rather than the input's default inline box: it
   centres the glyph below, and it is what `vertical-align: middle` on the cell
   actually centres — an inline input would sit on the text baseline instead. */
.stbl-check {
  appearance: none;
  -webkit-appearance: none;
  display: grid;
  place-content: center;
  margin: 0 auto;
  width: 15px;
  height: 15px;
  border: 1px solid var(--border-strong);
  border-radius: 0;
  background: var(--bg);
  cursor: pointer;
}
.stbl-check:checked,
.stbl-check:indeterminate {
  background: var(--epfl-red);
  border-color: var(--epfl-red);
}
/* Checkmark: two borders of an empty box, rotated. White in both themes — it sits
   on EPFL red, which never lightens. */
.stbl-check::after {
  content: '';
  width: 7px;
  height: 3px;
  border: 2px solid #fff;
  border-top: 0;
  border-right: 0;
  transform: translateY(-1px) rotate(-45deg);
  opacity: 0;
}
.stbl-check:checked::after {
  opacity: 1;
}
/* Indeterminate (some-but-not-all rows on the page): a bar, not a tick. */
.stbl-check:indeterminate::after {
  opacity: 1;
  width: 8px;
  height: 0;
  border-left: 0;
  transform: none;
}
.stbl-check:focus-visible {
  outline: 2px solid var(--epfl-red);
  outline-offset: 1px;
}
.stbl-check:disabled {
  cursor: not-allowed;
  opacity: 0.4;
}

/* Cell treatments (design tbl) */
.cell-mono {
  font-family: var(--font-sans);
  font-size: 12px;
}
.cell-strong {
  font-weight: 600;
}
.tag {
  /* global .tag pill, minus its border — a ruled pill per row reads too heavy in a table */
  border: 0;
}
/* Category value: a tag pill in the chart's color for that value — text in
   the color (pulled slightly toward ink so amber/sky stay legible) on a
   desaturated tint of it. Falls back to the muted grey until the dataset's
   scale is known. */
.cell-category {
  --category-color: #c1c1c1;
  color: color-mix(in srgb, var(--category-color) 80%, var(--fg));
  background: color-mix(in srgb, var(--category-color) 14%, var(--bg));
  white-space: nowrap;
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
  height: var(--stbl-head-h, 44px);
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

/* Only the Vuetify filter fields (filter-only row): stop the native number
   input's intrinsic min-width from bloating them. Scoped to `.table-input` so
   it doesn't catch the header-menu filter input, which must stay full width. */
:deep(.table-input input[type='number']) {
  width: 3em;
}

:deep(.v-list-item-title) {
  min-width: 200px;
}
</style>
