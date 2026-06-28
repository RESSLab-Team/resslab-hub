<script setup lang="ts">
import CheckboxDialog, { type CheckBoxDialogItem } from '@/components/commons/CheckboxDialog.vue'
import TextSubscript from '@/components/commons/TextSubscript.vue'
import { DownloadType, type Column, type ColumnType } from '@/composables/table'
import i18n from '@/plugins/i18n'
import { useNotificationStore } from '@/stores/notification'
import { shareCurrentUrl, type Searches } from '@/utils/common'
import { booleanOptions, type DataOptions } from '@/utils/vuetify'
import { mdiDownload, mdiMagnify, mdiShare } from '@mdi/js'
import { computed, ref, watch } from 'vue'
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

// TODO add genericity https://github.com/vuejs/rfcs/discussions/436
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type M = any
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
    hideToolbar: false
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
const selectedItems = ref<M[]>([])
const page = ref<number>(1)
const itemsPerPage = ref<number>(5)

watch(selectedItemsIds, (newIdList, oldIdList) => {
  const oldList = selectedItems.value
  const newIds = newIdList.filter((id) => !oldIdList.includes(id)),
    removedIds = oldIdList.filter((id) => !newIdList.includes(id))
  const newList = oldList
    .filter((item) => !removedIds.includes(item.id))
    .concat(newIds.map((id) => props.items.find((item) => item.id === id)))
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

const pageCount = computed<number>(() =>
  Math.max(1, Math.ceil(props.totalFilteredCount / itemsPerPage.value))
)
const pageFrom = computed<number>(() =>
  props.totalFilteredCount === 0 ? 0 : (page.value - 1) * itemsPerPage.value + 1
)
const pageTo = computed<number>(() =>
  Math.min(page.value * itemsPerPage.value, props.totalFilteredCount)
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

function isItemSelectable(item: M): boolean {
  return selectedItems.value.length < maxDownloadCount || selectedItemsIds.value.includes(item.id)
}

function resetFilters(): void {
  globalSearch.value = ''
  columnSearches.value = {}
}

// https://vuetifyjs.com/en/api/v-data-table-server/#events-click:row
// Vuetify 3.4+ emits the raw row as `item` (3.3 labs wrapped it as `item.raw`).
function click(_: Event, value: { item: M }): void {
  emit('click:row', value.item)
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
  <v-card class="stbl" flat>
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
    <v-data-table-server
      v-model="selectedItemsIds"
      v-model:page="page"
      v-model:items-per-page="itemsPerPage"
      density="compact"
      fixed-header
      :headers="tableHeaders"
      :items="items"
      :items-length="totalFilteredCount"
      :loading="loading"
      must-sort
      :search="search"
      :item-selectable="isItemSelectable"
      show-select
      :item-value="(item) => item.id"
      @click:row="click"
      @update:options="emit('update:options', $event)"
    >
      <template v-for="header in tableHeaders" :key="header.key" #[`column.${header.key}`]>
        <text-subscript :text="header.title" />
      </template>
      <template
        v-for="header in tableHeaders"
        :key="`item-${header.key}`"
        #[`item.${header.key}`]="{ internalItem }"
      >
        <span v-if="header.cellVariant === 'tag' && internalItem.columns[header.key]" class="tag">{{
          header.format
            ? header.format(internalItem.columns[header.key])
            : internalItem.columns[header.key]
        }}</span>
        <span
          v-else
          :class="{
            'cell-mono': header.cellVariant === 'mono',
            'cell-strong': header.cellVariant === 'strong'
          }"
          >{{
            header.format
              ? header.format(internalItem.columns[header.key])
              : internalItem.columns[header.key]
          }}</span
        >
      </template>

      <template v-if="!hideFilterOnly && filterHeaders.length" #top>
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
      </template>
      <template #thead>
        <tr>
          <td>
            <!-- select -->
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
                  style="color: blue"
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
      </template>
      <template #[`item.t_dp_tot`]="{ item }">
        <template
          v-if="
            //@ts-ignore
            item.t_dp_tot
          "
          >{{
            //@ts-ignore
            item.t_dp_tot
          }}</template
        >
      </template>
      <template #bottom>
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
                <strong>{{ pageTo }}</strong>
              </template>
              <template #total>
                <strong>{{ totalFilteredCount }}</strong>
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
      </template>
    </v-data-table-server>
    <checkbox-dialog
      ref="downloadDialog"
      :title="$t('commons.download')"
      :items="checkboxDialogItems"
      loading-on-confirm
    />
  </v-card>
</template>

<style lang="scss" scoped>
/* EPFL design-system table — mirrors the handoff's .tbl styles on top of
   v-data-table-server. */
.stbl {
  border: 1px solid var(--border);
  border-radius: 0;
  background: var(--bg);
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

:deep(.v-table) {
  font-size: 13px;
  font-feature-settings: 'tnum';
  background: var(--bg);
}

:deep(.v-table__wrapper) {
  max-height: 50vh;
  overflow-y: auto;
}

/* Column header row */
:deep(.v-table__wrapper) > table > thead > tr > th {
  background: var(--bg-subtle) !important;
  text-transform: uppercase;
  font-size: 11px;
  letter-spacing: 0.06em;
  font-weight: 700;
  color: var(--fg-muted);
  border-bottom: 1px solid var(--table-gridline-strong) !important;
  white-space: nowrap;
}

/* Filter row (custom thead slot) — design-handoff bordered inputs */
:deep(.v-table__wrapper) > table > thead > tr > td {
  background: var(--bg);
  border-bottom: 1px solid var(--table-gridline-strong) !important;
  padding: 6px 6px;
}
:deep(.v-table__wrapper) > table > thead > tr > td .v-field {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg);
  font-size: 12px;
  padding-inline-start: 8px;
}
:deep(.v-table__wrapper) > table > thead > tr > td .v-field--focused {
  outline: 2px solid var(--epfl-red);
  outline-offset: -1px;
}
:deep(.v-table__wrapper) > table > thead > tr > td .v-field--variant-plain .v-field__input {
  padding-top: 4px;
  padding-bottom: 4px;
  min-height: 28px;
  font-size: 12px;
  opacity: 1;
}
:deep(.v-table__wrapper) > table > thead > tr > td .v-field--variant-plain .v-label {
  font-size: 12px;
}
:deep(.v-table__wrapper) > table > thead > tr > td .v-field__clearable,
:deep(.v-table__wrapper) > table > thead > tr > td .v-field__append-inner {
  padding-top: 2px;
}

/* Body rows */
:deep(.v-table__wrapper) > table > tbody > tr > td {
  border-bottom: 1px solid var(--table-gridline) !important;
  white-space: nowrap;
}
:deep(.v-table__wrapper) > table > tbody > tr:hover {
  cursor: pointer;
  background: var(--bg-subtle);
}
:deep(.v-table__wrapper) > table > tbody > tr.v-data-table__tr--clickable:focus-visible,
:deep(.v-table__wrapper) > table > tbody > tr:has(.v-selection-control--dirty) {
  background: rgba(227, 7, 19, 0.05);
  box-shadow: inset 3px 0 0 var(--epfl-red);
}

/* Selection checkboxes — EPFL red when checked */
:deep(.v-selection-control--dirty .v-icon) {
  color: var(--epfl-red);
}

/* Cell treatments (design tbl) */
:deep(.cell-mono) {
  font-family: var(--font-mono);
  font-size: 12px;
}
:deep(.cell-strong) {
  font-weight: 600;
}

table > tr > td {
  padding-left: 16px;
  padding-right: 16px;
}

:deep(input[type='number']) {
  width: 3em;
}

:deep(.v-list-item-title) {
  min-width: 200px;
}
</style>
