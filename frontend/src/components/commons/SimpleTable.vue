<script setup lang="ts">
import CheckboxDialog, {
  CheckBoxDialogItem,
} from "@/components/commons/CheckboxDialog.vue";
import { filterColumnValue, globalSearchKey, Searches } from "@/utils/common";
import { booleanOptions } from "@/utils/vuetify";
import {
  withDefaults,
  defineProps,
  defineEmits,
  ref,
  computed,
  watch,
} from "vue";
import { DataOptions, DataTableHeader } from "vuetify";
import { Column, ColumnType, DownloadType } from "@/utils/table";
import i18n from "@/i18n";
import { useRoute } from "vue-router/composables";
import { useNotificationStore } from "@/stores/notification";

interface TableHeader extends DataTableHeader {
  type: ColumnType;
  options?: string[];
  multiple?: boolean;
}

// TODO add genericity https://github.com/vuejs/rfcs/discussions/436
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type T = any;
const props = withDefaults(
  defineProps<{
    title?: string;
    columns?: Column[];
    totalCount?: number;
    loading?: boolean;
    items?: T[];
    options?: DataOptions;
    totalFilteredCount?: number;
    prefix?: string;
    query?: string;
    searches?: Searches;
    search?: string;
  }>(),
  {
    title: undefined,
    columns: () => [],
    totalCount: undefined,
    loading: false,
    items: () => [],
    options: undefined,
    totalFilteredCount: undefined,
    prefix: undefined,
    query: undefined,
    searches: () => ({}),
    search: "",
  }
);
const emit = defineEmits<{
  (e: "update:options", value: DataOptions): void;
  (e: "download", items: T[], types: DownloadType[]): void;
  (e: "update:searches", value: Searches): void;
  (e: "update:search", value: string): void;
  (e: "click:row", value: T): void;
}>();

const maxDownloadCount = 5;
const checkboxDialogItems: CheckBoxDialogItem<DownloadType>[] = [
  {
    key: DownloadType.Main,
    text: "Master data",
  },
  {
    key: DownloadType.Test,
    text: "Test data",
  },
];

const route = useRoute();
const notificationStore = useNotificationStore();

const downloadDialog = ref<InstanceType<typeof CheckboxDialog>>();
const selectedItems = ref<T[]>([]);

const options = computed<DataOptions>({
  get: () => props.options,
  set: (value) => emit("update:options", value),
});
const columnSearches = computed<Searches>({
  get: () => props.searches,
  set: (value) => emit("update:searches", value),
});
const globalSearch = computed<string>({
  get: () => props.search,
  set: (value) => emit("update:search", value),
});
const tableHeaders = computed<TableHeader[]>(() =>
  props.columns.filter((column) => !column.filterOnly).map(getTableHeader)
);
const filterHeaders = computed<TableHeader[]>(() =>
  props.columns.filter((column) => column.filterOnly).map(getTableHeader)
);
const hasFilters = computed<boolean>(
  () =>
    globalSearch.value.length > 0 ||
    Object.values(columnSearches.value).filter(filterColumnValue).length > 0
);

watch(selectedItems, (value) => {
  if (value.length > maxDownloadCount) {
    notificationStore.notify(
      `You cannot download more than ${maxDownloadCount} items.`
    );
  }
});

function resetFilters(): void {
  globalSearch.value = "";
  columnSearches.value = {};
}

function click(item: T): void {
  emit("click:row", item);
}

function shareUrl(): void {
  const url = new URL(window.location.origin + route.path);
  Object.entries(columnSearches.value)
    .filter(([, value]) => filterColumnValue(value))
    .forEach(([key, value]) => {
      url.searchParams.append(key, value.toString());
    });
  if (globalSearch.value.length > 0) {
    url.searchParams.append(globalSearchKey, globalSearch.value);
  }
  const shareUrl = url.href;
  if (navigator.share) {
    navigator.share({
      url: shareUrl,
    });
    return;
  }
  if (navigator.clipboard) {
    navigator.clipboard.writeText(shareUrl);
    notificationStore.notify("Copied to clipboard");
    return;
  }
  if (shareUrl) {
    notificationStore.notify(shareUrl, shareUrl);
  }
}

function getTableHeader(column: Column): TableHeader {
  return {
    value: column.value,
    text: i18n.t(props.prefix + column.value).toString(),
    type: column.type,
    options: column.options?.sort(),
    multiple: column.options ? column.options.length > 2 : false,
  };
}

/**
 * Open download dialog for option selection, get files from backend, zip them and download the zip
 */
function downloadZip(): void {
  downloadDialog.value
    ?.open(`${selectedItems.value.length} selected`)
    .then((types) =>
      emit("download", selectedItems.value, types as DownloadType[])
    )
    .finally(() => {
      downloadDialog.value?.close();
    });
}
</script>

<template>
  <v-card>
    <v-card-title>
      <slot name="title">
        {{ title }}
      </slot>
      <v-spacer />
      <v-text-field
        v-model="globalSearch"
        clearable
        hide-details
        single-line
        append-icon="mdi-magnify"
        label="Search"
      />
      <v-btn color="primary" :disabled="!hasFilters" text @click="resetFilters">
        Reset filters
      </v-btn>
    </v-card-title>
    <v-data-table
      v-model="selectedItems"
      dense
      :headers="tableHeaders"
      :items="items"
      :items-per-page="5"
      :footer-props="{
        itemsPerPageOptions: [5, 10, 20, 100, 1000],
      }"
      :loading="loading"
      must-sort
      :options="options"
      :search="search"
      :server-items-length="totalFilteredCount"
      show-select
      :sort-by="tableHeaders[0].value"
      @click:row="click"
      @update:options="emit('update:options', $event)"
    >
      <template #top>
        <v-row class="px-4 pb-4">
          <v-col v-for="header in filterHeaders" :key="header.value">
            <v-select
              v-if="header.options"
              v-model="columnSearches[header.value]"
              clearable
              hide-details
              :label="header.text"
              :multiple="header.multiple"
              :items="header.options"
            >
            </v-select>
            <div v-else v-switch="header.type">
              <v-text-field
                v-model="columnSearches[header.value]"
                v-case="'text'"
                clearable
                hide-details
                :label="header.text"
              />
              <v-select
                v-model="columnSearches[header.value]"
                v-case="'boolean'"
                clearable
                hide-details
                :label="header.text"
                :items="booleanOptions"
              />
              <v-text-field
                v-model="columnSearches[header.value]"
                v-case="'number'"
                clearable
                hide-details
                hide-spin-buttons
                :label="header.text"
                type="number"
              />
            </div>
          </v-col>
        </v-row>
      </template>
      <template #[`body.prepend`]>
        <tr>
          <td>
            <!-- select -->
            <v-icon>mdi-magnify</v-icon>
          </td>
          <td v-for="header in tableHeaders" :key="header.value">
            <v-select
              v-if="header.options"
              v-model="columnSearches[header.value]"
              class="mt-0 pt-0"
              clearable
              hide-details
              :label="header.text"
              :multiple="header.multiple"
              :items="header.options"
              single-line
            >
              <template #item="{ item, on, attrs }">
                <slot
                  :name="`column.header.item.${header.value}`"
                  :item="item"
                  :on="on"
                  :attrs="attrs"
                />
              </template>
            </v-select>
            <div v-else v-switch="header.type">
              <v-text-field
                v-model="columnSearches[header.value]"
                v-case="'text'"
                class="mt-0 pt-0"
                clearable
                hide-details
                :label="header.text"
                single-line
              />
              <v-select
                v-model="columnSearches[header.value]"
                v-case="'boolean'"
                class="mt-0 pt-0"
                clearable
                hide-details
                :label="header.text"
                :items="booleanOptions"
                single-line
              />
              <v-text-field
                v-model="columnSearches[header.value]"
                v-case="'number'"
                class="mt-0 pt-0"
                clearable
                hide-details
                hide-spin-buttons
                :label="header.text"
                single-line
                type="number"
              />
            </div>
          </td>
        </tr>
      </template>
      <template #[`item.t_dp_tot`]="{ item }">
        <template v-if="item.t_dp_tot">{{ item.t_dp_tot }}</template>
      </template>
    </v-data-table>
    <v-card-actions>
      <v-btn
        color="primary"
        :disabled="
          selectedItems.length === 0 || selectedItems.length > maxDownloadCount
        "
        text
        @click="downloadZip"
      >
        <v-icon left>mdi-download</v-icon>
        Download ({{ selectedItems.length }}/{{ totalCount }})
      </v-btn>
      <v-btn color="primary" :disabled="!hasFilters" text @click="shareUrl">
        <v-icon left>mdi-share</v-icon>
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
:deep(.v-data-table__wrapper) > table > tbody > tr:hover {
  cursor: pointer;
}
</style>
