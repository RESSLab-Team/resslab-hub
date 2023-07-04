<script setup lang="ts">
import { ColumnField, type ColumnModel } from '@/backend'
import InfoTooltip from '@/components/commons/InfoTooltip.vue'
import SimpleTable from '@/components/commons/SimpleTable.vue'
import { tableProps, useTable, type Column, type TableEmits } from '@/composables/table'
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
    type: 'text'
  },
  {
    value: ColumnField.SectionC,
    type: 'text'
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
  () => columnsApi.getColumnsCounts(),
  (query, sortBy, sortDesc, page, size) =>
    columnsApi.getColumns(query, sortBy, sortDesc, page, size),
  (ids) => columnsApi.getColumnsCsv(ids),
  (message) => notificationStore.notify(message)
)
</script>

<template>
  <simple-table
    v-model:options="options"
    v-model:search="search"
    v-model:searches="searches"
    :columns="columns"
    :items="items"
    :loading="loading"
    prefix="column."
    :query="query"
    :total-count="totalCount"
    :total-filtered-count="totalFilteredCount"
    @click:row="clickRow"
    @download="downloadFiles"
  >
    <template #title>
      Columns
      <info-tooltip>
        <p>
          The Columns Database presents data from early 1970s on columns under reversed cyclic and
          monotonic loading. The primary data involve the deduced moment chord rotation of the
          column and deduced column axial shortening versus chord rotation.
        </p>
        How to use?
        <ul>
          <li>
            Filter the table by making selections in the various plots around the table, or by using
            the filters and dropdowns above the table headers.
          </li>
          <li>Click on a row to see the data of a single test.</li>
          <li>
            Download specific tests results by selecting the test (left-most column) and click
            "Download" below.
          </li>
          <li>
            Share specific tests results by selecting the test (left-most column) and click "Share"
            below.
          </li>
        </ul>
      </info-tooltip>
    </template>
  </simple-table>
</template>
