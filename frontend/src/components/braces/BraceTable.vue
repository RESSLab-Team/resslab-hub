<script setup lang="ts">
import { BraceField, BraceModel } from "@/backend";
import InfoTooltip from "@/components/commons/InfoTooltip.vue";
import SimpleTable from "@/components/commons/SimpleTable.vue";
import { bracesApi } from "@/plugins/axios";
import { useNotificationStore } from "@/stores/notification";
import { Searches } from "@/utils/common";
import { useTable, Column } from "@/utils/table";
import {
  withDefaults,
  defineProps,
  defineEmits,
  ref,
  computed,
  toRef,
} from "vue";
import { DataOptions } from "vuetify";

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
  (e: "update:searches", value: Searches): void;
  (e: "update:search", value: string): void;
  (e: "click:row", value: BraceModel): void;
}>();

const columns: Column[] = [
  {
    value: BraceField.Investigator,
    type: "text",
  },
  {
    value: BraceField.SpecimenId,
    type: "text",
  },
  {
    value: BraceField.CrossSectionSize,
    type: "text",
  },
  {
    value: BraceField.Steel,
    type: "text",
  },
  {
    value: BraceField.KlR,
    type: "number",
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
  useTable<BraceModel>(
    "brace",
    options,
    toRef(props, "query"),
    [
      {
        name: "displacement",
        countKey: "displacement_count",
        getCsv: (id) => bracesApi.getBracesDisplacementCsv(id),
      },
    ],
    () => bracesApi.getBracesCounts(),
    (query, sortBy, sortDesc, page, size) =>
      bracesApi.getBraces(query, sortBy, sortDesc, page, size),
    (ids) => bracesApi.getBracesCsv(ids),
    (message) => notificationStore.notify(message)
  );
</script>

<template>
  <simple-table
    :columns="columns"
    :items="items"
    :loading="loading"
    :options.sync="options"
    prefix="brace."
    :query="query"
    :search.sync="globalSearch"
    :searches.sync="searches"
    :total-count="totalCount"
    :total-filtered-count="totalFilteredCount"
    @click:row="emit('click:row', $event)"
    @download="downloadFiles"
  >
    <template #title>
      Braces
      <info-tooltip>
        <p>
          The Brace Database presents data from mid 1970s on steel braces of
          various configurations. The braces are subjected to monotonic,
          symmetric cyclic and other loading histories. The primary data involve
          the brace axial load versus axial displacement.
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
