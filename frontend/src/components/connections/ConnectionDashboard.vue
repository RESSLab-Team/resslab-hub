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
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

const { t } = useI18n({ useScope: 'global' })

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

// Hoisted to stable references so the double-charts that consume them don't get
// a fresh array prop (and thus re-render) on every dashboard re-render.
const typeYearFields: [ConnectionField, ConnectionField] = [
  ConnectionField.Date,
  ConnectionField.ConnectionType
]
const columnDoublerFields: [ConnectionField, ConnectionField] = [
  ConnectionField.DC,
  ConnectionField.NDp
]

const railGroups = computed<FilterRailGroup[]>(() => [
  {
    key: ConnectionField.ConnectionType,
    label: t('dashboards.connection.rail_connection_type'),
    icon: mdiTagOutline,
    type: 'chips',
    redChips: true,
    options: ['WUF-W', 'RBS', 'WUF-B', 'BFP', 'WFP', 'KBB', 'BEEP']
  },
  {
    key: ConnectionField.Date,
    label: t('dashboards.connection.rail_test_date'),
    icon: mdiCalendarRange,
    type: 'range',
    min: 1970,
    max: 2026
  },
  {
    key: ConnectionField.Northridge,
    label: t('dashboards.connection.rail_northridge'),
    icon: mdiHistory,
    type: 'chips',
    options: [
      { label: 'Pre-1994', value: 'pre' },
      { label: 'Post-1994', value: 'post' }
    ]
  },
  {
    key: ConnectionField.SpecimenType,
    label: t('dashboards.connection.rail_specimen_type'),
    icon: mdiViewGridOutline,
    type: 'chips',
    options: [
      { label: 'Interior', value: 'interior%' },
      { label: 'Exterior', value: 'exterior%' }
    ]
  },
  {
    key: ConnectionField.Slab,
    label: t('dashboards.connection.rail_composite_slab'),
    icon: mdiLayersOutline,
    type: 'chips',
    options: [
      { label: 'Bare', value: 'false' },
      { label: 'Composite', value: 'true' }
    ]
  },
  {
    key: ConnectionField.NDp,
    label: t('dashboards.connection.rail_doubler_plates'),
    icon: mdiLayersTriple,
    type: 'chips',
    options: [
      { label: 'None', value: '0' },
      { label: 'With', value: '> 0' }
    ]
  },
  {
    key: ConnectionField.DB,
    label: t('dashboards.connection.rail_beam_depth'),
    icon: mdiTune,
    type: 'range'
  },
  {
    key: ConnectionField.TCf,
    label: t('dashboards.connection.rail_column_flange'),
    icon: mdiTune,
    type: 'range'
  },
  {
    key: ConnectionField.GMaxGY,
    label: t('dashboards.connection.rail_panel_zone'),
    icon: mdiPulse,
    type: 'range'
  }
])
</script>

<template>
  <dashboard-shell
    v-model:search="search"
    :eyebrow="$t('dashboards.common.eyebrow_components')"
    :title="$t('dashboards.connection.title')"
    :count="countsStore.counts.connections"
    :description="$t('dashboards.connection.description')"
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
        <chart-cell
          :title="$t('dashboards.connection.chart_tests_per_year_type')"
          :hint="$t('dashboards.common.hint_click_legend_to_filter')"
          :field="typeYearFields"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <connection-double-chart
            :color="periwinkle"
            :fields="typeYearFields"
            type="line"
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell
          quiet
          :title="$t('dashboards.connection.chart_connection_type')"
          :hint="$t('dashboards.common.hint_click_tile_to_filter')"
          :field="ConnectionField.ConnectionType"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <connection-single-chart
            :color="peach"
            :field="ConnectionField.ConnectionType"
            :show-reset="false"
            flat
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell
          quiet
          :title="$t('dashboards.connection.chart_beam_steel_grade')"
          :hint="$t('dashboards.common.hint_click_to_filter')"
          :field="ConnectionField.SteelB"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <connection-single-chart
            :color="cobalt"
            :field="ConnectionField.SteelB"
            :show-reset="false"
            flat
            @change:searches="changeSearches"
          />
        </chart-cell>
      </div>

      <!-- Row 2: stacked histograms -->
      <div class="charts-strip charts-strip-2cols">
        <chart-cell
          :title="$t('dashboards.connection.chart_beam_depth_slab')"
          :hint="$t('dashboards.common.hint_stacked_histogram')"
          :field="beamFields"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <connection-double-chart
            :color="sky"
            :fields="beamFields"
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell
          :title="$t('dashboards.connection.chart_column_depth_doubler_plates')"
          :hint="$t('dashboards.common.hint_stacked_histogram')"
          :field="columnDoublerFields"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <connection-double-chart
            :color="plum"
            :fields="columnDoublerFields"
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
