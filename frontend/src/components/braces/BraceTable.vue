<script setup lang="ts">
import { BraceField, type BraceModel } from '@/backend'
import InfoTooltip from '@/components/commons/InfoTooltip.vue'
import SimpleTable from '@/components/commons/SimpleTable.vue'
import { tableProps, useTable, type Column, type TableEmits } from '@/composables/table'
import { bracesApi } from '@/plugins/axios'
import { useNotificationStore } from '@/stores/notification'
import { toRef } from 'vue'

const columns: Column[] = [
  {
    value: BraceField.Investigator,
    type: 'text'
  },
  {
    value: BraceField.SpecimenId,
    type: 'text'
  },
  {
    value: BraceField.CrossSectionSize,
    type: 'text'
  },
  {
    value: BraceField.Steel,
    type: 'text'
  },
  {
    value: BraceField.KlR,
    title: 'kL/r<sub>y</sub>',

    type: 'number'
  }
]

const props = defineProps(tableProps)
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends TableEmits<BraceModel> {}
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
} = useTable<BraceModel>(
  emit,
  'brace',
  toRef(props, 'query'),
  toRef(props, 'search'),
  toRef(props, 'searches'),
  [
    {
      name: 'displacement',
      countKey: 'displacement_count',
      getCsv: (id) => bracesApi.getBracesDisplacementCsv(id)
    }
  ],
  () => bracesApi.getBracesCounts(),
  (query, sortBy, sortDesc, page, size) => bracesApi.getBraces(query, sortBy, sortDesc, page, size),
  (ids) => bracesApi.getBracesCsv(ids),
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
    prefix="brace."
    :query="query"
    :total-count="totalCount"
    :total-filtered-count="totalFilteredCount"
    @click:row="clickRow"
    @download="downloadFiles"
  >
    <template #title>
      Braces
      <info-tooltip>
        <p>
          The Brace Database presents data from mid 1970s on steel braces of various configurations.
          The braces are subjected to monotonic, symmetric cyclic and other loading histories. The
          primary data involve the brace axial load versus axial displacement.
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
