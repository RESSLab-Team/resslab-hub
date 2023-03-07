<script setup lang="ts">
import { MaterialField, MaterialModel } from "@/backend";
import SimpleTable from "@/components/commons/SimpleTable.vue";
import { materialsApi } from "@/plugins/axios";
import { Column, TableEmits, tableProps, useTable } from "@/composables/table";
import { defineProps, defineEmits, toRef } from "vue";
import { useNotificationStore } from "@/stores/notification";

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

const props = defineProps(tableProps);
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends TableEmits<MaterialModel> {}
const emit = defineEmits<Emits>();

const notificationStore = useNotificationStore();
const {
  clickRow,
  downloadFiles,
  items,
  loading,
  options,
  search,
  searches,
  totalCount,
  totalFilteredCount,
} = useTable<MaterialModel>(
  emit,
  "material",
  toRef(props, "query"),
  toRef(props, "search"),
  toRef(props, "searches"),
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
    :search.sync="search"
    :searches.sync="searches"
    title="Materials"
    :total-count="totalCount"
    :total-filtered-count="totalFilteredCount"
    @click:row="clickRow"
    @download="downloadFiles"
  />
</template>
