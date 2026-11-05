<script setup lang="ts">
import { ColumnField, type ColumnModel } from '@/backend'
import ChartCell from '@/components/commons/ChartCell.vue'
import DashboardShell from '@/components/commons/DashboardShell.vue'
import ColumnDoubleChart from '@/components/columns/charts/ColumnDoubleChart.vue'
import ColumnParallelChart from '@/components/columns/charts/ColumnParallelChart.vue'
import ColumnSingleChart from '@/components/columns/charts/ColumnSingleChart.vue'
import ColumnDetail from '@/components/columns/ColumnDetail.vue'
import ColumnTable from '@/components/columns/ColumnTable.vue'
import { COLUMN_KEY, PARALLEL_FIELDS, fetchColumns } from '@/components/columns/data'
import type { DoubleFields } from '@/composables/chart'
import { useDashboard } from '@/composables/dashboard'
import { useAutoFilters } from '@/composables/useAutoFilters'
import { useCountsStore } from '@/stores/counts'
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const { clickTableRow, closeDetail, item, query, search, searches, changeSearches } =
  useDashboard<ColumnModel>(route, router, ColumnField, {
    key: COLUMN_KEY,
    fetchAll: fetchColumns
  })

const countsStore = useCountsStore()
onMounted(() => countsStore.fetch())

const parallelFields = PARALLEL_FIELDS

const parallelFilterFields: string[] = [
  ColumnField.Id,
  ...parallelFields.flatMap((f) =>
    typeof f.id === 'string'
      ? [f.id]
      : 'dividend' in f.id
      ? [`${f.id.dividend}/${f.id.divisor}`]
      : []
  )
]
const boundaryConditionFields: DoubleFields<ColumnField> = [
  ColumnField.Date,
  ColumnField.BoundaryCondition
]
const columnDepthFields: DoubleFields<ColumnField> = [
  ColumnField.DC,
  {
    id: ColumnField.BuiltUp,
    mapping: new Map([
      ['False', 'Hot Rolled'],
      ['True', 'Built Up']
    ])
  }
]

// Filters are derived from the data dictionary + the loaded dataset, so a new
// column becomes filterable without touching this file, and fieldGroups.ts
// decides which category of the rail it shows up under.
const {
  filters,
  groups: filterGroups,
  loading: filtersLoading
} = useAutoFilters({
  database: 'columns',
  datasetKey: COLUMN_KEY,
  fetchAll: fetchColumns,
  i18nPrefix: 'column.'
})
</script>

<template>
  <dashboard-shell
    v-model:search="search"
    :eyebrow="$t('dashboards.common.eyebrow_components')"
    :title="$t('dashboards.column.title')"
    :count="countsStore.counts.columns"
    :description="$t('dashboards.column.description')"
    database-id="columns"
    i18n-prefix="column."
    :filters="filters"
    :filter-groups="filterGroups"
    :filters-loading="filtersLoading"
    :searches="searches"
    :detail-open="!!item"
    @change:searches="changeSearches"
    @close:detail="closeDetail"
  >
    <template #table>
      <column-table
        v-model:search="search"
        v-model:searches="searches"
        :query="query"
        @click:row="clickTableRow"
      />
    </template>

    <template #charts>
      <div class="charts-strip">
        <chart-cell
          :title="$t('dashboards.column.chart_tests_per_year_bc')"
          :hint="$t('dashboards.common.hint_click_legend_to_filter')"
          :field="boundaryConditionFields"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <column-double-chart
            :fields="boundaryConditionFields"
            type="line"
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell
          :title="$t('dashboards.column.chart_column_depth_fabrication')"
          :hint="$t('dashboards.common.hint_stacked_histogram')"
          :field="columnDepthFields"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <column-double-chart :fields="columnDepthFields" @change:searches="changeSearches" />
        </chart-cell>
        <chart-cell
          quiet
          :title="$t('dashboards.column.chart_steel_grade')"
          :hint="$t('dashboards.common.hint_click_to_filter')"
          :field="ColumnField.SteelC"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <column-single-chart
            :field="ColumnField.SteelC"
            :show-reset="false"
            flat
            @change:searches="changeSearches"
          />
        </chart-cell>
      </div>

      <div class="charts-strip charts-strip-1col">
        <chart-cell
          :title="$t('commons.parallel_view_title')"
          :hint="$t('commons.parallel_view_hint')"
          :field="parallelFilterFields"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <column-parallel-chart :fields="parallelFields" @change:searches="changeSearches" />
        </chart-cell>
      </div>
    </template>

    <template #detail>
      <column-detail v-if="item" :column="item" @close="closeDetail" />
    </template>
  </dashboard-shell>
</template>
