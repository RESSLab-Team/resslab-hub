<script setup lang="ts">
import { ResidualStressField, type ResidualStressModel } from '@/backend'
import SimpleTable from '@/components/commons/SimpleTable.vue'
import { tableProps, useTable, type Column, type TableEmits } from '@/composables/table'
import { subscribeCrossfilter } from '@/composables/crossfilterBus'
import { useDataset } from '@/composables/useDataset'
import { RESIDUAL_KEY, fetchResiduals } from '@/components/residuals/data'
import { residualsApi } from '@/plugins/axios'
import { useNotificationStore } from '@/stores/notification'
import { formatNumber } from '@/utils/formatter'
import { onUnmounted, ref, toRef } from 'vue'

const columns: Column[] = [
  {
    value: ResidualStressField.ExperimentalProgram,
    type: 'text'
  },
  {
    value: ResidualStressField.Profile,
    type: 'text',
    cellVariant: 'mono'
  },
  {
    value: ResidualStressField.Steel,
    type: 'text'
  },
  {
    value: ResidualStressField.Tf,
    type: 'number',
    title: 't<sub>f</sub> [mm]'
  },
  {
    value: ResidualStressField.HOverB,
    title: 'h/b<sub>f</sub>',
    type: 'number',
    format: (value) => formatNumber(value, 2)
  }
]

const props = defineProps(tableProps)
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends TableEmits<ResidualStressModel> {}
const emit = defineEmits<Emits>()

const notificationStore = useNotificationStore()
const { getTotal, getPage, countRowsSync, pageSync } = useDataset<ResidualStressModel>(
  RESIDUAL_KEY,
  fetchResiduals
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
} = useTable<ResidualStressModel>(
  emit,
  'residual',
  toRef(props, 'query'),
  toRef(props, 'search'),
  toRef(props, 'searches'),
  [
    {
      name: 'distribution-f1',
      countKey: 'distribution_F1_count',
      getCsv: (id) => residualsApi.getResidualStressesDistributionF1Csv(id)
    },
    {
      name: 'distribution-f2',
      countKey: 'distribution_F2_count',
      getCsv: (id) => residualsApi.getResidualStressesDistributionF2Csv(id)
    },
    {
      name: 'distribution-w1',
      countKey: 'distribution_W1_count',
      getCsv: (id) => residualsApi.getResidualStressesDistributionW1Csv(id)
    }
  ],
  getTotal,
  getPage,
  (ids) => residualsApi.getResidualStressesCsv(ids),
  (message) => notificationStore.notify(message)
)

// Live crossfilter: during a brush drag, stream the table's current page live from
// the in-memory dataset — the light-DOM virtualized body re-renders its visible
// rows in a few ms, so rows can track the drag frame-for-frame like the charts.
// `liveItems` replaces the body rows and `liveCount` drives the footer text; both
// are display-only (pagination still rides the committed totalFilteredCount, so no
// page-clamp refetch). Both clear on pointer-up, when the reactive commit settles.
const liveCount = ref<number>()
const liveItems = ref<ResidualStressModel[]>()
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
    prefix="residual."
    :query="query"
    :title="$t('table.residual.title')"
    :total-count="totalCount"
    :total-filtered-count="totalFilteredCount"
    @click:row="clickRow"
    @download="downloadFiles"
  />
</template>
