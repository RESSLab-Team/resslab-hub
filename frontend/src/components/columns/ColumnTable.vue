<script setup lang="ts">
import { ColumnField, type ColumnModel } from '@/backend'
import SimpleTable from '@/components/commons/SimpleTable.vue'
import { tableProps, useTable, type Column, type TableEmits } from '@/composables/table'
import { useDataset } from '@/composables/useDataset'
import { COLUMN_KEY, fetchColumns } from '@/components/columns/data'
import { columnsApi } from '@/plugins/axios'
import { useNotificationStore } from '@/stores/notification'
import { toRef } from 'vue'

const columns: Column[] = [
  {
    value: ColumnField.ExperimentalProgram,
    type: 'text'
  },
  {
    value: ColumnField.SpecimenDesignation,
    type: 'text',
    cellVariant: 'strong'
  },
  {
    value: ColumnField.SectionC,
    type: 'text',
    cellVariant: 'mono'
  },
  {
    value: ColumnField.PGOverPYm,
    title: 'P<sub>g</sub>/P<sub>y</sub>',

    type: 'number'
  },
  {
    value: ColumnField.LBOverRYc,
    title: 'L<sub>b</sub>/r<sub>y</sub>',

    type: 'number'
  },
  {
    value: ColumnField.DirectionLp,
    type: 'text'
  }
]

const props = defineProps(tableProps)
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends TableEmits<ColumnModel> {}
const emit = defineEmits<Emits>()

const notificationStore = useNotificationStore()
const { getTotal, getPage, countRowsSync, pageSync } = useDataset<ColumnModel>(
  COLUMN_KEY,
  fetchColumns
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
} = useTable<ColumnModel>(
  emit,
  'column',
  toRef(props, 'query'),
  toRef(props, 'search'),
  toRef(props, 'searches'),
  [
    {
      name: 'axial-shortening',
      countKey: 'axial_shortening_count',
      getCsv: (id) => columnsApi.getColumnsAxialShorteningCsv(id)
    },
    {
      name: 'moment-strong',
      countKey: 'moment_strong_count',
      getCsv: (id) => columnsApi.getColumnsMomentStrongCsv(id)
    },
    {
      name: 'moment-weak',
      countKey: 'moment_weak_count',
      getCsv: (id) => columnsApi.getColumnsMomentWeakCsv(id)
    }
  ],
  getTotal,
  getPage,
  (ids) => columnsApi.getColumnsCsv(ids),
  (message) => notificationStore.notify(message),
  { countRowsSync, pageSync } // live crossfilter rows during a drag (see useTable)
)
</script>

<template>
  <simple-table
    v-model:options="options"
    v-model:searches="searches"
    database-id="columns"
    :columns="columns"
    :live-count="liveCount"
    :live-items="liveItems"
    :items="items"
    instant
    :loading="loading"
    prefix="column."
    :query="query"
    :total-count="totalCount"
    :total-filtered-count="totalFilteredCount"
    @click:row="clickRow"
    @download="downloadFiles"
  >
  </simple-table>
</template>
