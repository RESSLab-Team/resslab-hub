<script setup lang="ts">
import { DuctileFractureField, type DuctileFractureModel } from '@/backend'
import SimpleTable from '@/components/commons/SimpleTable.vue'
import { tableProps, useTable, type Column, type TableEmits } from '@/composables/table'
import { useDataset } from '@/composables/useDataset'
import { DUCTILE_FRACTURE_KEY, fetchDuctileFractures } from '@/components/ductile-fracture/data'
import { ductileFractureApi } from '@/plugins/axios'
import { useNotificationStore } from '@/stores/notification'
import { displayLoading } from '@/utils/ductile_fracture'
import { toRef } from 'vue'

const columns: Column[] = [
  {
    value: DuctileFractureField.ExperimentalProgram,
    type: 'text'
  },
  {
    value: DuctileFractureField.SpecimenDesignation,
    type: 'text',
    cellVariant: 'strong'
  },
  {
    value: DuctileFractureField.SteelType,
    categoryColor: true,
    type: 'text'
  },
  {
    value: DuctileFractureField.Loading,
    type: 'text',
    format: (value: unknown) => displayLoading(value as string | null | undefined)
  },
  {
    value: DuctileFractureField.SpecimenType,
    categoryColor: true,
    type: 'text',
    cellVariant: 'tag'
  },
  {
    value: DuctileFractureField.SectionType,
    type: 'text',
    titleKey: 'table.ductile_fracture.columns.profileType'
  }
]

const props = defineProps(tableProps)
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends TableEmits<DuctileFractureModel> {}
const emit = defineEmits<Emits>()

const notificationStore = useNotificationStore()
const { getTotal, getPage, countRowsSync, pageSync, colorFor } = useDataset<DuctileFractureModel>(
  DUCTILE_FRACTURE_KEY,
  fetchDuctileFractures
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
} = useTable<DuctileFractureModel>(
  emit,
  'ductile-fracture',
  toRef(props, 'query'),
  toRef(props, 'search'),
  toRef(props, 'searches'),
  [
    {
      name: 'force-elongation',
      countKey: 'force_elongation_count',
      getCsv: (id) => ductileFractureApi.getDuctileFracturesForceElongationCsv(id)
    },
    {
      name: 'force-elongation-simulation',
      countKey: 'force_elongation_simulation_count',
      getCsv: (id) => ductileFractureApi.getDuctileFracturesForceElongationSimulationCsv(id)
    },
    {
      name: 'force-radial',
      countKey: 'force_radial_count',
      getCsv: (id) => ductileFractureApi.getDuctileFracturesForceRadialCsv(id)
    },
    {
      name: 'force-radial-simulation',
      countKey: 'force_radial_simulation_count',
      getCsv: (id) => ductileFractureApi.getDuctileFracturesForceRadialSimulationCsv(id)
    },
    {
      name: 'epeq-simulation',
      countKey: 'epeq_simulation_count',
      getCsv: (id) => ductileFractureApi.getDuctileFracturesEpeqSimulationCsv(id)
    },
    {
      name: 'lode-simulation',
      countKey: 'lode_simulation_count',
      getCsv: (id) => ductileFractureApi.getDuctileFracturesLodeSimulationCsv(id)
    },
    {
      name: 'triax-simulation',
      countKey: 'triax_simulation_count',
      getCsv: (id) => ductileFractureApi.getDuctileFracturesTriaxSimulationCsv(id)
    }
  ],
  getTotal,
  getPage,
  (ids) => ductileFractureApi.getDuctileFracturesCsv(ids),
  (message) => notificationStore.notify(message),
  { countRowsSync, pageSync } // live crossfilter rows during a drag (see useTable)
)
</script>

<template>
  <simple-table
    v-model:options="options"
    v-model:searches="searches"
    :color-for="colorFor"
    database-id="ductile-fracture"
    :columns="columns"
    :live-count="liveCount"
    :live-items="liveItems"
    :items="items"
    instant
    :loading="loading"
    prefix="ductile_fracture."
    :query="query"
    :total-count="totalCount"
    :total-filtered-count="totalFilteredCount"
    @click:row="clickRow"
    @download="downloadFiles"
  />
</template>
