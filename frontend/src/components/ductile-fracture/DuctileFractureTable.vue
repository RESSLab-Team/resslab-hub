<script setup lang="ts">
import { DuctileFractureField, type DuctileFractureModel } from '@/backend'
import SimpleTable from '@/components/commons/SimpleTable.vue'
import { tableProps, useTable, type Column, type TableEmits } from '@/composables/table'
import { ductileFractureApi } from '@/plugins/axios'
import { useNotificationStore } from '@/stores/notification'
import { displayLoading } from '@/utils/ductile_fracture'
import { toRef } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const columns: Column[] = [
  {
    value: DuctileFractureField.ExperimentalProgram,
    type: 'text'
  },
  {
    value: DuctileFractureField.SteelType,
    type: 'text'
  },
  {
    value: DuctileFractureField.Loading,
    type: 'text',
    format: (value: unknown) => displayLoading(value as string | null | undefined)
  },
  {
    value: DuctileFractureField.SpecimenType,
    type: 'text',
    cellVariant: 'tag'
  },
  {
    value: DuctileFractureField.SectionType,
    type: 'text',
    title: t('table.ductile_fracture.columns.profileType')
  }
]

const props = defineProps(tableProps)
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends TableEmits<DuctileFractureModel> {}
const emit = defineEmits<Emits>()

const notificationStore = useNotificationStore()
const {
  clickRow,
  downloadFiles,
  items,
  loading,
  options,
  search,
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
  () => ductileFractureApi.getDuctileFracturesCounts(),
  (query, sortBy, sortDesc, page, size) =>
    ductileFractureApi.getDuctileFractures(query, sortBy, sortDesc, page, size),
  (ids) => ductileFractureApi.getDuctileFracturesCsv(ids),
  (message) => notificationStore.notify(message)
)
</script>

<template>
  <simple-table
    v-model:options="options"
    v-model:search="search"
    v-model:searches="searches"
    :columns="columns"
    hide-toolbar
    :items="items"
    :loading="loading"
    prefix="ductile_fracture."
    :query="query"
    :title="$t('table.ductile_fracture.title')"
    :total-count="totalCount"
    :total-filtered-count="totalFilteredCount"
    @click:row="clickRow"
    @download="downloadFiles"
  />
</template>
