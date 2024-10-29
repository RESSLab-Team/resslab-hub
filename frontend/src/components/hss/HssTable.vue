<script setup lang="ts">
import { HSSColumnField, type HSSColumnModel } from '@/backend'
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
  />
</template>
