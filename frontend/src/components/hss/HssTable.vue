<script setup lang="ts">
import { HSSColumnField, type HSSColumnModel } from '@/backend'
import SimpleTable from '@/components/commons/SimpleTable.vue'
import { tableProps, useTable, type Column, type TableEmits } from '@/composables/table'
import { useDataset } from '@/composables/useDataset'
import { HSS_KEY, fetchHsss } from '@/components/hss/data'
import { hssApi } from '@/plugins/axios'
import { useNotificationStore } from '@/stores/notification'
import { toRef } from 'vue'

const columns: Column[] = [
  {
    value: HSSColumnField.Investigator,
    type: 'text'
  },
  {
    value: HSSColumnField.Id,
    type: 'text',
    cellVariant: 'strong',
    format: (value: unknown) => String(value ?? '').replaceAll('_', ' ')
  },
  {
    value: HSSColumnField.TubeSection,
    type: 'text',
    cellVariant: 'mono'
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
const emit = defineEmits<TableEmits<HSSColumnModel>>()

const notificationStore = useNotificationStore()
const { getTotal, getPage, countRowsSync, pageSync } = useDataset<HSSColumnModel>(
  HSS_KEY,
  fetchHsss
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
  getTotal,
  getPage,
  (ids) => hssApi.getHssColumnsCsv(ids),
  (message) => notificationStore.notify(message),
  { countRowsSync, pageSync } // live crossfilter rows during a drag (see useTable)
)
</script>

<template>
  <simple-table
    v-model:options="options"
    v-model:searches="searches"
    database-id="hss"
    :columns="columns"
    :items="items"
    :live-count="liveCount"
    :live-items="liveItems"
    instant
    :loading="loading"
    prefix="hss."
    :query="query"
    :total-count="totalCount"
    :total-filtered-count="totalFilteredCount"
    @click:row="clickRow"
    @download="downloadFiles"
  >
  </simple-table>
</template>
