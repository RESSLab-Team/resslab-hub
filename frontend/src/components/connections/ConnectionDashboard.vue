<script setup lang="ts">
import { ConnectionField, type ConnectionModel } from '@/backend'
import ChartCell from '@/components/commons/ChartCell.vue'
import DashboardShell from '@/components/commons/DashboardShell.vue'
import type { FilterRailGroup } from '@/components/commons/FilterRail.vue'
import ConnectionDoubleChart from '@/components/connections/charts/ConnectionDoubleChart.vue'
import ConnectionParallelChart from '@/components/connections/charts/ConnectionParallelChart.vue'
import ConnectionSingleChart from '@/components/connections/charts/ConnectionSingleChart.vue'
import ConnectionDetail from '@/components/connections/ConnectionDetail.vue'
import ConnectionTable from '@/components/connections/ConnectionTable.vue'
import type { DoubleFields, ParallelField } from '@/composables/chart'
import { useDashboard } from '@/composables/dashboard'
import { useCountsStore } from '@/stores/counts'
import { cobalt, peach, periwinkle, plum, sky } from '@/utils/vuetify'
import {
  mdiCalendarRange,
  mdiHistory,
  mdiLayersOutline,
  mdiLayersTriple,
  mdiPulse,
  mdiTagOutline,
  mdiTune,
  mdiViewGridOutline
} from '@mdi/js'
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const { clickTableRow, closeDetail, item, query, search, searches, changeSearches, updatePage } =
  useDashboard<ConnectionModel>(route, router, ConnectionField)

const countsStore = useCountsStore()
onMounted(() => countsStore.fetch())

const parallelFields: ParallelField<ConnectionField>[] = [
  {
    id: ConnectionField.DB,
    name: 'Beam Depth\ndb [mm]'
  },
  {
    id: ConnectionField.DC,
    name: 'Column Depth\ndc [mm]'
  },
  {
    id: ConnectionField.TCf,
    name: 'Column flange\nThickness [mm]'
  },
  {
    id: {
      dividend: ConnectionField.DB,
      divisor: ConnectionField.DC
    },
    name: 'db / dc'
  },
  {
    id: ConnectionField.GMaxGY
  },
  {
    id: ConnectionField.RuRnPlN
  },
  {
    id: ConnectionField.ConnectionType,
    name: 'Connection\nType'
  }
]
const beamFields: DoubleFields<ConnectionField> = [
  ConnectionField.DB,
  {
    id: ConnectionField.Slab,
    mapping: new Map([
      ['False', 'Bare'],
      ['True', 'Composite']
    ])
  }
]

const railGroups: FilterRailGroup[] = [
  {
    key: ConnectionField.ConnectionType,
    label: 'Connection type',
    icon: mdiTagOutline,
    type: 'chips',
    redChips: true,
    options: ['WUF-W', 'RBS', 'WUF-B', 'BFP', 'WFP', 'KBB', 'BEEP']
  },
  {
    key: ConnectionField.Date,
    label: 'Test date',
    icon: mdiCalendarRange,
    type: 'range',
    min: 1970,
    max: 2026
  },
  {
    key: ConnectionField.Northridge,
    label: 'Northridge',
    icon: mdiHistory,
    type: 'chips',
    options: [
      { label: 'Pre-1994', value: 'pre' },
      { label: 'Post-1994', value: 'post' }
    ]
  },
  {
    key: ConnectionField.SpecimenType,
    label: 'Specimen type',
    icon: mdiViewGridOutline,
    type: 'chips',
    options: [
      { label: 'Interior', value: 'interior%' },
      { label: 'Exterior', value: 'exterior%' }
    ]
  },
  {
    key: ConnectionField.Slab,
    label: 'Composite slab',
    icon: mdiLayersOutline,
    type: 'chips',
    options: [
      { label: 'Bare', value: 'false' },
      { label: 'Composite', value: 'true' }
    ]
  },
  {
    key: ConnectionField.NDp,
    label: 'Doubler plates',
    icon: mdiLayersTriple,
    type: 'chips',
    options: [
      { label: 'None', value: '0' },
      { label: 'With', value: '> 0' }
    ]
  },
  {
    key: ConnectionField.DB,
    label: 'Beam depth db [mm]',
    icon: mdiTune,
    type: 'range'
  },
  {
    key: ConnectionField.TCf,
    label: 'Column flange tcf [mm]',
    icon: mdiTune,
    type: 'range'
  },
  {
    key: ConnectionField.GMaxGY,
    label: 'Panel-zone γmax/γy',
    icon: mdiPulse,
    type: 'range'
  }
]
</script>

<template>
  <dashboard-shell
    v-model:search="search"
    eyebrow="Components · Database"
    title="Connections"
    :count="countsStore.counts.connections"
    description="Beam-to-column moment connection tests under reversed cyclic and monotonic loading,
      categorized per AISC-358-16. Filter through the filters panel, the table column filters or
      the charts below; click a row for the full specimen detail and digitized test data."
    i18n-prefix="connection."
    :rail-groups="railGroups"
    :searches="searches"
    :detail-open="!!item"
    @change:searches="changeSearches"
    @close:detail="closeDetail"
  >
    <template #table>
      <connection-table
        v-model:search="search"
        v-model:searches="searches"
        :query="query"
        @click:row="clickTableRow"
        @update:page="updatePage"
      />
    </template>

    <template #charts>
      <!-- Row 1: distributions -->
      <div class="charts-strip">
        <chart-cell quiet title="Connection type" hint="Click a tile to filter">
          <connection-single-chart
            :color="peach"
            :field="ConnectionField.ConnectionType"
            :query="query"
            :show-reset="false"
            flat
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell title="Tests per year × type" hint="Click legend to filter">
          <connection-double-chart
            :color="periwinkle"
            :fields="[ConnectionField.Date, ConnectionField.ConnectionType]"
            :query="query"
            type="line"
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell quiet title="Beam steel grade" hint="Click to filter">
          <connection-single-chart
            :color="cobalt"
            :field="ConnectionField.SteelB"
            :query="query"
            :show-reset="false"
            flat
            @change:searches="changeSearches"
          />
        </chart-cell>
      </div>

      <!-- Row 2: stacked histograms -->
      <div class="charts-strip charts-strip-2cols">
        <chart-cell title="Beam depth × slab" hint="Stacked histogram · click bar or legend">
          <connection-double-chart
            :color="sky"
            :fields="beamFields"
            :query="query"
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell
          title="Column depth × doubler plates"
          hint="Stacked histogram · click bar or legend"
        >
          <connection-double-chart
            :color="plum"
            :fields="[ConnectionField.DC, ConnectionField.NDp]"
            :query="query"
            @change:searches="changeSearches"
          />
        </chart-cell>
      </div>

      <!-- Row 3: parallel coordinates (full width) -->
      <div class="charts-strip charts-strip-1col">
        <chart-cell>
          <connection-parallel-chart
            :color="periwinkle"
            :fields="parallelFields"
            :query="query"
            @change:searches="changeSearches"
          />
        </chart-cell>
      </div>
    </template>

    <template #detail>
      <connection-detail v-if="item" :connection="item" @close="closeDetail" />
    </template>
  </dashboard-shell>
</template>
