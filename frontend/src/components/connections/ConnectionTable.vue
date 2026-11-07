<script setup lang="ts">
import { ConnectionField, type ConnectionModel } from '@/backend'
import SimpleTable from '@/components/commons/SimpleTable.vue'
import { tableProps, useTable, type Column, type TableEmits } from '@/composables/table'
import { useDataset } from '@/composables/useDataset'
import { CONNECTION_KEY, fetchConnections } from '@/components/connections/data'
import { connectionsApi } from '@/plugins/axios'
import { useNotificationStore } from '@/stores/notification'
import { getConnectionTypeImage } from '@/utils/component'
import { toRef } from 'vue'

const columns: Column[] = [
  {
    value: ConnectionField.ExperimentalProgram,
    type: 'text'
  },
  {
    value: ConnectionField.SpecimenDesignation,
    type: 'text',
    cellVariant: 'strong'
  },
  {
    value: ConnectionField.ConnectionType,
    categoryColor: true,
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
    value: ConnectionField.TDpTot,
    type: 'number'
  }
]

const props = defineProps(tableProps)
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends TableEmits<ConnectionModel> {}
const emit = defineEmits<Emits>()

const notificationStore = useNotificationStore()
const { getTotal, getPage, countRowsSync, pageSync, colorFor } = useDataset<ConnectionModel>(
  CONNECTION_KEY,
  fetchConnections
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
  (message) => notificationStore.notify(message),
  { countRowsSync, pageSync } // live crossfilter rows during a drag (see useTable)
)

function getImageSource(item: string): string {
  return getConnectionTypeImage(item)
}
</script>

<template>
  <simple-table
    v-model:options="options"
    v-model:searches="searches"
    :color-for="colorFor"
    database-id="connections"
    :columns="columns"
    instant
    :live-count="liveCount"
    :live-items="liveItems"
    :items="items"
    :loading="loading"
    prefix="connection."
    :query="query"
    :total-count="totalCount"
    :total-filtered-count="totalFilteredCount"
    @click:row="clickRow"
    @download="downloadFiles"
  >
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
