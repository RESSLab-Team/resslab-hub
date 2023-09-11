<script setup lang="ts">
import CheckboxDialog, { type CheckBoxDialogItem } from '@/components/commons/CheckboxDialog.vue'
import TextSubscript from '@/components/commons/TextSubscript.vue'
import { DownloadType, type Column, type ColumnType } from '@/composables/table'
import i18n from '@/plugins/i18n'
import { useNotificationStore } from '@/stores/notification'
import { filterColumnValue, globalSearchKey, type Searches } from '@/utils/common'
import { booleanOptions, type DataOptions } from '@/utils/vuetify'
import { mdiDownload, mdiMagnify, mdiShare } from '@mdi/js'
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

interface TableHeader {
  type: ColumnType
  multiple?: boolean
  options?: string[]
  format?: (value: unknown) => string
  // https://github.com/vuetifyjs/vuetify/blob/master/packages/vuetify/src/labs/VDataTable/types.ts
  key: string
  title: string
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
    search: ''
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
const vInputBind = {
  class: 'table-input',
  clearable: true,
  density: 'compact' as 'compact',
  hideDetails: true,
  singleLine: true,
  variant: 'underlined' as 'underlined'
}
const checkboxDialogItems: CheckBoxDialogItem<DownloadType>[] = [
  {
    key: DownloadType.Main,
    text: 'Master data'
  },
  {
    key: DownloadType.Test,
    text: 'Test data'
  }
]

const route = useRoute()
const notificationStore = useNotificationStore()

const downloadDialog = ref<InstanceType<typeof CheckboxDialog>>()
const selectedItemsIds = ref<string[]>([])
const selectedItems = ref<M[]>([])

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

watch(selectedItems, (value) => {
  if (value.length >= maxDownloadCount) {
    notificationStore.notify(`You cannot download more than ${maxDownloadCount} items.`)
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
function click(_: Event, value: { item: { raw: M } }): void {
  emit('click:row', value.item.raw)
}

function shareUrl(): void {
  const url = new URL(window.location.origin + route.path)
  Object.entries(columnSearches.value)
    .filter(([, value]) => filterColumnValue(value))
    .forEach(([key, value]) => {
      url.searchParams.append(key, value.toString())
    })
  if (globalSearch.value.length > 0) {
    url.searchParams.append(globalSearchKey, globalSearch.value)
  }
  const shareUrl = url.href
  if (navigator.share) {
    navigator.share({
      url: shareUrl
    })
    return
  }
  if (navigator.clipboard) {
    navigator.clipboard.writeText(shareUrl)
    notificationStore.notify('Copied to clipboard')
    return
  }
  if (shareUrl) {
    notificationStore.notify(shareUrl, shareUrl)
  }
}

function getTableHeader(column: Column): TableHeader {
  return {
    key: column.value,
    title: column.title ?? i18n.global.t(props.prefix + column.value).toString(),
    type: column.type,
    format: column.format,
    options: column.options?.sort(),
    multiple: column.options ? column.options.length > 2 : false
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
  <v-card>
    <v-card-title class="d-flex">
      <slot name="title">
        {{ title }}
      </slot>
      <v-spacer />
      <v-responsive class="mx-1" max-width="256">
        <v-text-field
          v-model="globalSearch"
          clearable
          density="compact"
          hide-details
          single-line
          :prepend-inner-icon="mdiMagnify"
          label="Search"
          variant="outlined"
        />
      </v-responsive>
      <v-btn color="primary" :disabled="!hasFilters" variant="text" @click="resetFilters">
        Reset filters
      </v-btn>
    </v-card-title>
    <v-data-table-server
      v-model="selectedItemsIds"
      density="compact"
      fixed-header
      :headers="tableHeaders"
      :items="items"
      :items-length="totalFilteredCount"
      :items-per-page="5"
      :footer-props="{
        itemsPerPageOptions: [5, 10, 20, 100, 1000]
      }"
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
      <template v-for="header in tableHeaders" #[`item.${header.key}`]="{ item }">
        {{ header.format ? header.format(item.columns[header.key]) : item.columns[header.key] }}
      </template>

      <template #top>
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
              v-bind="vInputBind"
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
              v-bind="vInputBind"
              v-model="columnSearches[header.key]"
              :label="header.title"
            >
              <template #label> <text-subscript :text="header.title"></text-subscript> </template>
            </v-text-field>
            <v-select
              v-else-if="header.type === 'boolean'"
              v-bind="vInputBind"
              v-model="columnSearches[header.key]"
              :label="header.title"
              :items="booleanOptions"
            >
              <template #label> <text-subscript :text="header.title"></text-subscript> </template>
            </v-select>
            <v-text-field
              v-else-if="header.type === 'number'"
              v-bind="vInputBind"
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
    </v-data-table-server>
    <v-card-actions>
      <v-btn
        color="primary"
        :disabled="selectedItems.length === 0 || selectedItems.length > maxDownloadCount"
        :prepend-icon="mdiDownload"
        @click="downloadZip"
      >
        Download ({{ selectedItems.length }}/{{ totalCount }})
      </v-btn>
      <v-btn color="primary" :disabled="!hasFilters" :prepend-icon="mdiShare" @click="shareUrl">
        Share
      </v-btn>
    </v-card-actions>
    <checkbox-dialog
      ref="downloadDialog"
      title="Download"
      :items="checkboxDialogItems"
      loading-on-confirm
    />
  </v-card>
</template>

<style lang="scss" scoped>
:deep(.v-table__wrapper) {
  max-height: 50vh;
  overflow-y: auto;
}

:deep(.v-table__wrapper) > table > tbody > tr:hover {
  cursor: pointer;
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
