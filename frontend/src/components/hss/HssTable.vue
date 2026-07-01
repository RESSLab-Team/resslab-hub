<script setup lang="ts">
import { HSSColumnField, type HSSColumnModel } from '@/backend'
import InfoTooltip from '@/components/commons/InfoTooltip.vue'
import SimpleTable from '@/components/commons/SimpleTable.vue'
import { tableProps, useTable, type Column, type TableEmits } from '@/composables/table'
import { subscribeCrossfilter } from '@/composables/crossfilterBus'
import { useDataset } from '@/composables/useDataset'
import { HSS_KEY, fetchHsss } from '@/components/hss/data'
import { hssApi } from '@/plugins/axios'
import { useNotificationStore } from '@/stores/notification'
import { onUnmounted, ref, toRef } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })

const columns: Column[] = [
  {
    value: HSSColumnField.Investigator,
    title: t('table.hss.columns.experimentalProgram'),
    type: 'text'
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
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends TableEmits<HSSColumnModel> {}
const emit = defineEmits<Emits>()

const notificationStore = useNotificationStore()
const { getTotal, getPage, countRowsSync, pageSync } = useDataset<HSSColumnModel>(
  HSS_KEY,
  fetchHsss
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
  (message) => notificationStore.notify(message)
)

// Live crossfilter: during a brush drag, stream the table's current page live from
// the in-memory dataset — the light-DOM virtualized body re-renders its visible
// rows in a few ms, so rows can track the drag frame-for-frame like the charts.
// `liveItems` replaces the body rows and `liveCount` drives the footer text; both
// are display-only (pagination still rides the committed totalFilteredCount, so no
// page-clamp refetch). Both clear on pointer-up, when the reactive commit settles.
const liveCount = ref<number>()
const liveItems = ref<HSSColumnModel[]>()
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
    :items="items"
    :live-count="liveCount"
    :live-items="liveItems"
    instant
    :loading="loading"
    prefix="hss."
    :query="query"
    :title="$t('table.hss.title')"
    :total-count="totalCount"
    :total-filtered-count="totalFilteredCount"
    @click:row="clickRow"
    @download="downloadFiles"
  >
    <template #title>
      {{ $t('table.hss.title') }}
      <info-tooltip>
        <p>{{ $t('table.hss.tooltip.intro') }}</p>
        {{ $t('table.hss.tooltip.howToUse') }}
        <ul>
          <li>{{ $t('table.hss.tooltip.bulletFilter') }}</li>
          <li>{{ $t('table.hss.tooltip.bulletClick') }}</li>
          <li>{{ $t('table.hss.tooltip.bulletDownload') }}</li>
          <li>{{ $t('table.hss.tooltip.bulletShare') }}</li>
        </ul>
      </info-tooltip>
    </template>
  </simple-table>
</template>
