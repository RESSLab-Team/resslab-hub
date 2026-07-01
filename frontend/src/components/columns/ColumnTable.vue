<script setup lang="ts">
import { ColumnField, type ColumnModel } from '@/backend'
import InfoTooltip from '@/components/commons/InfoTooltip.vue'
import SimpleTable from '@/components/commons/SimpleTable.vue'
import { tableProps, useTable, type Column, type TableEmits } from '@/composables/table'
import { subscribeCrossfilter } from '@/composables/crossfilterBus'
import { useDataset } from '@/composables/useDataset'
import { COLUMN_KEY, fetchColumns } from '@/components/columns/data'
import { columnsApi } from '@/plugins/axios'
import { useNotificationStore } from '@/stores/notification'
import { onUnmounted, ref, toRef } from 'vue'

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
  getTotal,
  getPage,
  (ids) => columnsApi.getColumnsCsv(ids),
  (message) => notificationStore.notify(message)
)

// Live crossfilter: during a brush drag, stream the table's current page live from
// the in-memory dataset — the light-DOM virtualized body re-renders its visible
// rows in a few ms, so rows can track the drag frame-for-frame like the charts.
// `liveItems` replaces the body rows and `liveCount` drives the footer text; both
// are display-only (pagination still rides the committed totalFilteredCount, so no
// page-clamp refetch). Both clear on pointer-up, when the reactive commit settles.
const liveCount = ref<number>()
const liveItems = ref<ColumnModel[]>()
const unsubscribeCrossfilter = subscribeCrossfilter({
  onLive: (liveQuery) => {
    liveCount.value = countRowsSync(liveQuery)
    const opts = options.value
    liveItems.value = pageSync(
      liveQuery,
      opts?.sortBy?.map((sort) => sort.key),
      opts?.sortBy?.map((sort) => sort.order === 'desc'),
      opts?.page,
      opts?.itemsPerPage === -1 ? 1000 : opts?.itemsPerPage
    )
  },
  onSettle: () => {
    liveCount.value = undefined
    liveItems.value = undefined
  }
})
onUnmounted(unsubscribeCrossfilter)
</script>

<template>
  <simple-table
    v-model:options="options"
    v-model:search="search"
    v-model:searches="searches"
    :columns="columns"
    hide-toolbar
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
    <template #title>
      {{ $t('table.column.title') }}
      <info-tooltip>
        <p>{{ $t('table.column.tooltip.intro') }}</p>
        {{ $t('table.column.tooltip.howToUse') }}
        <ul>
          <li>{{ $t('table.column.tooltip.bulletFilter') }}</li>
          <li>{{ $t('table.column.tooltip.bulletClick') }}</li>
          <li>{{ $t('table.column.tooltip.bulletDownload') }}</li>
          <li>{{ $t('table.column.tooltip.bulletShare') }}</li>
        </ul>
      </info-tooltip>
    </template>
  </simple-table>
</template>
