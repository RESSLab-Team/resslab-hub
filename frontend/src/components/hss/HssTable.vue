<script setup lang="ts">
import { HSSColumnField, type HSSColumnModel } from '@/backend'
import InfoTooltip from '@/components/commons/InfoTooltip.vue'
import SimpleTable from '@/components/commons/SimpleTable.vue'
import { tableProps, useTable, type Column, type TableEmits } from '@/composables/table'
import { hssApi } from '@/plugins/axios'
import { useNotificationStore } from '@/stores/notification'
import { toRef } from 'vue'

const columns: Column[] = [
  {
    value: HSSColumnField.Investigator,
    title: 'Experimental Program',
    type: 'text'
  },
  {
    value: HSSColumnField.TubeSection,
    type: 'text'
  },
  {
    value: HSSColumnField.AxialLoadRatio,
    type: 'text'
  },
  {
    value: HSSColumnField.DepthOverT,
    type: 'number'
  },
  {
    value: HSSColumnField.LoadingAngle,
    type: 'number'
  }
]

const props = defineProps(tableProps)
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends TableEmits<HSSColumnModel> {}
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
} = useTable<HSSColumnModel>(
  emit,
  'hss',
  toRef(props, 'query'),
  toRef(props, 'search'),
  toRef(props, 'searches'),
  [
    {
      name: 'moment-rotation',
      countKey: 'moment_rotation_count',
      getCsv: (id) => hssApi.getHssColumnsMomentRotationCsv(id)
    }
  ],
  () => hssApi.getHssColumnsCounts(),
  (query, sortBy, sortDesc, page, size) =>
    hssApi.getHssColumns(query, sortBy, sortDesc, page, size),
  (ids) => hssApi.getHssColumnsCsv(ids),
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
    prefix="hss."
    :query="query"
    title="HSS Columns"
    :total-count="totalCount"
    :total-filtered-count="totalFilteredCount"
    @click:row="clickRow"
    @download="downloadFiles"
  >
    <template #title>
      HSS Columns
      <info-tooltip>
        <p>
          The HSS Columns Database presents data from early 1975 on columns under reversed cyclic
          and monotonic loading. The primary data involve the deduced moment chord rotation of the
          column.
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
