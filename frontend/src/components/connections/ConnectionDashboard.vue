<script setup lang="ts">
import { ConnectionField, type ConnectionModel } from '@/backend'
import ChartCell from '@/components/commons/ChartCell.vue'
import DashboardShell from '@/components/commons/DashboardShell.vue'
import ConnectionDoubleChart from '@/components/connections/charts/ConnectionDoubleChart.vue'
import ConnectionParallelChart from '@/components/connections/charts/ConnectionParallelChart.vue'
import ConnectionSingleChart from '@/components/connections/charts/ConnectionSingleChart.vue'
import ConnectionDetail from '@/components/connections/ConnectionDetail.vue'
import ConnectionTable from '@/components/connections/ConnectionTable.vue'
import { CONNECTION_KEY, PARALLEL_FIELDS, fetchConnections } from '@/components/connections/data'
import type { DoubleFields } from '@/composables/chart'
import { useDashboard } from '@/composables/dashboard'
import { useAutoFilters } from '@/composables/useAutoFilters'
import { useCountsStore } from '@/stores/counts'
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const { clickTableRow, closeDetail, item, query, search, searches, changeSearches } =
  useDashboard<ConnectionModel>(route, router, ConnectionField, {
    key: CONNECTION_KEY,
    fetchAll: fetchConnections
  })

const countsStore = useCountsStore()
onMounted(() => countsStore.fetch())

const parallelFields = PARALLEL_FIELDS

const parallelFilterFields: string[] = [
  ConnectionField.Id,
  ...parallelFields.flatMap((f) =>
    typeof f.id === 'string'
      ? [f.id]
      : 'dividend' in f.id
      ? [`${f.id.dividend}/${f.id.divisor}`]
      : []
  )
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

// Filters are derived from the data dictionary + the loaded dataset, so a new
// column becomes filterable without touching this file, and fieldGroups.ts
// decides which category of the rail it shows up under.
const {
  filters,
  groups: filterGroups,
  loading: filtersLoading
} = useAutoFilters({
  database: 'connections',
  datasetKey: CONNECTION_KEY,
  fetchAll: fetchConnections,
  i18nPrefix: 'connection.'
})
</script>

<template>
  <dashboard-shell
    v-model:search="search"
    :eyebrow="$t('dashboards.common.eyebrow_components')"
    :title="$t('dashboards.connection.title')"
    :count="countsStore.counts.connections"
    :description="$t('dashboards.connection.description')"
    database-id="connections"
    i18n-prefix="connection."
    :filters="filters"
    :filter-groups="filterGroups"
    :filters-loading="filtersLoading"
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
          <connection-double-chart :fields="beamFields" @change:searches="changeSearches" />
        </chart-cell>
        <chart-cell
          :title="$t('dashboards.connection.chart_column_depth_doubler_plates')"
          :hint="$t('dashboards.common.hint_stacked_histogram')"
          :field="columnDoublerFields"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <connection-double-chart
            :fields="columnDoublerFields"
            @change:searches="changeSearches"
          />
        </chart-cell>
      </div>

      <!-- Row 3: parallel coordinates (full width) -->
      <div class="charts-strip charts-strip-1col">
        <chart-cell
          :title="$t('commons.parallel_view_title')"
          :hint="$t('commons.parallel_view_hint')"
          :field="parallelFilterFields"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <connection-parallel-chart :fields="parallelFields" @change:searches="changeSearches" />
        </chart-cell>
      </div>
    </template>

    <template #detail>
      <connection-detail v-if="item" :connection="item" @close="closeDetail" />
    </template>
  </dashboard-shell>
</template>
