<script setup lang="ts">
import { MaterialField, MaterialModel } from "@/backend";
import SimpleTable from "@/components/commons/SimpleTable.vue";
import { materialsApi } from "@/plugins/axios";
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
  (e: "click:row", value: MaterialModel): void;
}>();

const columns: Column[] = [
  {
    value: MaterialField.ExperimentalProgram,
    type: "text",
  },
  {
    value: MaterialField.Id,
    type: "text",
  },
  {
    value: MaterialField.Type,
    type: "text",
  },
  {
    value: MaterialField.Profile,
    type: "text",
  },
  {
    value: MaterialField.Source,
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
  useTable<MaterialModel>(
    "material",
    options,
    toRef(props, "query"),
    [
      {
        name: "stress-strain",
        countKey: "stress_strain_count",
        getCsv: (id) => materialsApi.getMaterialsStressStrainCsv(id),
      },
    ],
    () => materialsApi.getMaterialsCounts(),
    (query, sortBy, sortDesc, page, size) =>
      materialsApi.getMaterials(query, sortBy, sortDesc, page, size),
    (ids) => materialsApi.getMaterialsCsv(ids),
    (message) => notificationStore.notify(message)
  );
</script>

<template>
  <simple-table
    :columns="columns"
    :items="items"
    :loading="loading"
    :options.sync="options"
    prefix="material."
    :query="query"
    :search.sync="globalSearch"
    :searches.sync="searches"
    title="Materials"
    :total-count="totalCount"
    :total-filtered-count="totalFilteredCount"
    @click:row="emit('click:row', $event)"
    @download="downloadFiles"
  />
</template>
