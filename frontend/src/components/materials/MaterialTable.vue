<script setup lang="ts">
import { MaterialField, type MaterialModel } from '@/backend'
import SimpleTable from '@/components/commons/SimpleTable.vue'
import { tableProps, useTable, type Column, type TableEmits } from '@/composables/table'
import { useDataset } from '@/composables/useDataset'
import { MATERIAL_KEY, fetchMaterials } from '@/components/materials/data'
import { materialsApi } from '@/plugins/axios'
import { useNotificationStore } from '@/stores/notification'
import { toRef } from 'vue'

const columns: Column[] = [
  {
    value: MaterialField.ExperimentalProgram,
    type: 'text'
  },
  {
    value: MaterialField.Id,
    type: 'text',
    cellVariant: 'strong'
  },
  {
    value: MaterialField.Type,
    categoryColor: true,
    type: 'text'
  },
  {
    value: MaterialField.Profile,
    type: 'text'
  },
  {
    value: MaterialField.Source,
    type: 'text'
  }
]

const props = defineProps(tableProps)
const emit = defineEmits<TableEmits<MaterialModel>>()

const notificationStore = useNotificationStore()
const { getTotal, getPage, countRowsSync, pageSync, colorFor } = useDataset<MaterialModel>(
  MATERIAL_KEY,
  fetchMaterials
)
const {
  clickRow,
  downloadFiles,
  items,
  liveCount,
  liveItems,
  loading,
  options,
  searches,
  totalCount,
  totalFilteredCount
} = useTable<MaterialModel>(
  emit,
  'material',
  toRef(props, 'query'),
  toRef(props, 'search'),
  toRef(props, 'searches'),
  [
    {
      name: 'stress-strain',
      countKey: 'stress_strain_count',
      getCsv: (id) => materialsApi.getMaterialsStressStrainCsv(id)
    }
  ],
  getTotal,
  getPage,
  (ids) => materialsApi.getMaterialsCsv(ids),
  (message) => notificationStore.notify(message),
  { countRowsSync, pageSync } // live crossfilter rows during a drag (see useTable)
)
</script>

<template>
  <simple-table
    v-model:options="options"
    v-model:searches="searches"
    :color-for="colorFor"
    database-id="cyclic"
    :columns="columns"
    :live-count="liveCount"
    :live-items="liveItems"
    :items="items"
    instant
    :loading="loading"
    prefix="material."
    :query="query"
    :total-count="totalCount"
    :total-filtered-count="totalFilteredCount"
    @click:row="clickRow"
    @download="downloadFiles"
  />
</template>
