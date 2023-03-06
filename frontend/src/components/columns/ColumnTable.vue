<script setup lang="ts">
import { ColumnField, ColumnModel } from "@/backend";
import InfoTooltip from "@/components/commons/InfoTooltip.vue";
import SimpleTable from "@/components/commons/SimpleTable.vue";
import { columnsApi } from "@/plugins/axios";
import { Searches } from "@/utils/common";
import { Column, useTable } from "@/utils/table";
import {
  withDefaults,
  defineProps,
  defineEmits,
  ref,
  computed,
  toRef,
} from "vue";
import { DataOptions } from "vuetify";
import { useNotificationStore } from "@/stores/notification";
import { Page } from "@/utils/backend";

const props = withDefaults(
  defineProps<{
    query?: string;
    searches?: Searches;
    search?: string;
  }>(),
  {
    query: undefined,
    searches: () => ({}),
    search: "",
  }
);
const emit = defineEmits<{
  (e: "click:row", value: ColumnModel): void;
  (e: "update:page", value: Page<ColumnModel>): void;
  (e: "update:search", value: string): void;
  (e: "update:searches", value: Searches): void;
}>();

const columns: Column[] = [
  {
    value: ColumnField.ExperimentalProgram,
    type: "text",
  },
  {
    value: ColumnField.SpecimenDesignation,
    type: "text",
  },
  {
    value: ColumnField.SectionC,
    type: "text",
  },
  {
    value: ColumnField.PGOverPYm,
    type: "number",
  },
  {
    value: ColumnField.LBOverRYc,
    type: "number",
  },
  {
    value: ColumnField.DirectionLp,
    type: "text",
  },
];

const options = ref<DataOptions>();

const searches = computed<Searches>({
  get: () => props.searches,
  set: (value) => emit("update:searches", value),
});
const globalSearch = computed<string>({
  get: () => props.search,
  set: (value) => emit("update:search", value),
});

const notificationStore = useNotificationStore();
const { downloadFiles, items, loading, totalCount, totalFilteredCount } =
  useTable<ColumnModel>(
    "column",
    options,
    toRef(props, "query"),
    [
      {
        name: "axial-shortening",
        countKey: "axial_shortening_count",
        getCsv: (id) => columnsApi.getColumnsAxialShorteningCsv(id),
      },
      {
        name: "moment-strong",
        countKey: "moment_strong_count",
        getCsv: (id) => columnsApi.getColumnsMomentStrongCsv(id),
      },
      {
        name: "moment-weak",
        countKey: "moment_weak_count",
        getCsv: (id) => columnsApi.getColumnsMomentWeakCsv(id),
      },
    ],
    () => columnsApi.getColumnsCounts(),
    (query, sortBy, sortDesc, page, size) =>
      columnsApi.getColumns(query, sortBy, sortDesc, page, size),
    (ids) => columnsApi.getColumnsCsv(ids),
    (message) => notificationStore.notify(message),
    (page) => emit("update:page", page)
  );
</script>

<template>
  <simple-table
    :columns="columns"
    :items="items"
    :loading="loading"
    :options.sync="options"
    prefix="column."
    :query="query"
    :search.sync="globalSearch"
    :searches.sync="searches"
    :total-count="totalCount"
    :total-filtered-count="totalFilteredCount"
    @click:row="emit('click:row', $event)"
    @download="downloadFiles"
  >
    <template #title>
      Columns
      <info-tooltip>
        <p>
          The Columns Database presents data from early 1970s on columns under
          reversed cyclic and monotonic loading. The primary data involve the
          deduced moment chord rotation of the column and deduced column axial
          shortening versus chord rotation.
        </p>
        How to use?
        <ul>
          <li>
            Filter the table by making selections in the various plots around
            the table, or by using the filters and dropdowns above the table
            headers.
          </li>
          <li>Click on a row to see the data of a single test.</li>
          <li>
            Download specific tests results by selecting the test (left-most
            column) and click "Download" below.
          </li>
          <li>
            Share specific tests results by selecting the test (left-most
            column) and click "Share" below.
          </li>
        </ul>
      </info-tooltip>
    </template>
  </simple-table>
</template>
