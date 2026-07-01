<script setup lang="ts">
import { ConnectionField, type ConnectionModel } from '@/backend'
import InfoTooltip from '@/components/commons/InfoTooltip.vue'
import SimpleTable from '@/components/commons/SimpleTable.vue'
import { tableProps, useTable, type Column, type TableEmits } from '@/composables/table'
import { subscribeCrossfilter } from '@/composables/crossfilterBus'
import { useDataset } from '@/composables/useDataset'
import { CONNECTION_KEY, fetchConnections } from '@/components/connections/data'
import { connectionsApi } from '@/plugins/axios'
import { useNotificationStore } from '@/stores/notification'
import { publicPath } from '@/utils/common'
import { onUnmounted, ref, toRef } from 'vue'

const columns: Column[] = [
  {
    value: ConnectionField.ExperimentalProgram,
    type: 'text'
  },
  {
    value: ConnectionField.Date,
    type: 'number',
    filterOnly: true
  },
  {
    value: ConnectionField.SpecimenDesignation,
    type: 'text',
    cellVariant: 'strong'
  },
  {
    value: ConnectionField.Northridge,
    type: 'option',
    options: ['pre', 'post'],
    filterOnly: true
  },
  {
    value: ConnectionField.SpecimenType,
    type: 'text',
    options: ['exterior%', 'interior%'],
    filterOnly: true
  },
  {
    value: ConnectionField.Slab,
    type: 'boolean',
    filterOnly: true
  },
  {
    value: ConnectionField.ConnectionType,
    type: 'option',
    options: ['WUF-W', 'RBS', 'WUF-B', 'BFP', 'WFP', 'KBB', 'BEEP'],
    cellVariant: 'tag'
  },
  {
    value: ConnectionField.SectionB,
    type: 'text',
    cellVariant: 'mono'
  },
  {
    value: ConnectionField.SectionC,
    type: 'text',
    cellVariant: 'mono'
  },
  {
    value: ConnectionField.NDp,
    type: 'number',
    options: ['0', '> 0'],
    filterOnly: true
  },
  {
    value: ConnectionField.TDpTot,
    type: 'number'
  }
]

const props = defineProps(tableProps)
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends TableEmits<ConnectionModel> {}
const emit = defineEmits<Emits>()

const notificationStore = useNotificationStore()
const { getTotal, getPage, countRowsSync } = useDataset<ConnectionModel>(
  CONNECTION_KEY,
  fetchConnections
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
} = useTable<ConnectionModel>(
  emit,
  'connection',
  toRef(props, 'query'),
  toRef(props, 'search'),
  toRef(props, 'searches'),
  [
    {
      name: 'beam',
      countKey: 'beam_count',
      getCsv: (id) => connectionsApi.getConnectionsBeamCsv(id)
    },
    {
      name: 'beam-west',
      countKey: 'beam_west_count',
      getCsv: (id) => connectionsApi.getConnectionsBeamWestCsv(id)
    },
    {
      name: 'global',
      countKey: 'global_count',
      getCsv: (id) => connectionsApi.getConnectionsGlobalCsv(id)
    },
    {
      name: 'global-west',
      countKey: 'global_west_count',
      getCsv: (id) => connectionsApi.getConnectionsGlobalWestCsv(id)
    },
    {
      name: 'panel-zone',
      countKey: 'panel_zone_count',
      getCsv: (id) => connectionsApi.getConnectionsPanelZonesCsv(id)
    }
  ],
  getTotal,
  getPage,
  (ids) => connectionsApi.getConnectionsCsv(ids),
  (message) => notificationStore.notify(message)
)

// Live crossfilter: surface ONLY a provisional filtered count during a drag, via a
// display-only `liveCount` that feeds the footer text but NOT pagination/items —
// re-rendering the data rows per frame is a ~40-70ms Vuetify patch (a long task),
// and touching the real count could make the server-table clamp the page and
// refetch mid-drag. The rows + real count settle on pointer-up (reactive commit).
const liveCount = ref<number>()
const unsubscribeCrossfilter = subscribeCrossfilter({
  onLive: (liveQuery) => {
    liveCount.value = countRowsSync(liveQuery)
  },
  onSettle: () => {
    liveCount.value = undefined
  }
})
onUnmounted(unsubscribeCrossfilter)

function getImageSource(item: string): string {
  return publicPath + 'img/connection-type/' + item.toLowerCase() + '.svg'
}
</script>

<template>
  <simple-table
    v-model:options="options"
    v-model:search="search"
    v-model:searches="searches"
    :columns="columns"
    hide-filter-only
    hide-toolbar
    instant
    :live-count="liveCount"
    :items="items"
    :loading="loading"
    prefix="connection."
    :query="query"
    :total-count="totalCount"
    :total-filtered-count="totalFilteredCount"
    @click:row="clickRow"
    @download="downloadFiles"
  >
    <template #title>
      {{ $t('table.connection.title') }}
      <info-tooltip>
        <p>{{ $t('table.connection.tooltip.intro') }}</p>
        {{ $t('table.connection.tooltip.howToUse') }}
        <ul>
          <li>{{ $t('table.connection.tooltip.bulletFilter') }}</li>
          <li>{{ $t('table.connection.tooltip.bulletClick') }}</li>
          <li>{{ $t('table.connection.tooltip.bulletDownload') }}</li>
          <li>{{ $t('table.connection.tooltip.bulletShare') }}</li>
        </ul>
      </info-tooltip>
    </template>
    <!-- eslint-disable-next-line vue/no-template-shadow -->
    <template #[`header-select-item.connection_type`]="{ props }">
      <v-list-item v-bind="props" @click="props.onClick as VoidFunction">
        <template #prepend="{ isSelected }">
          <v-checkbox hide-details :model-value="isSelected" :ripple="false" />
          <v-img max-height="128" width="128" :src="getImageSource(props.value as string)" />
        </template>
      </v-list-item>
    </template>
  </simple-table>
</template>
