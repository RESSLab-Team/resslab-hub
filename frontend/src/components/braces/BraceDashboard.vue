<script setup lang="ts">
import { BraceField, type BraceModel } from '@/backend'
import BraceDetail from '@/components/braces/BraceDetail.vue'
import BraceTable from '@/components/braces/BraceTable.vue'
import DatasetDoubleChart from '@/components/commons/charts/DatasetDoubleChart.vue'
import DatasetParallelChart from '@/components/commons/charts/DatasetParallelChart.vue'
import DatasetSingleChart from '@/components/commons/charts/DatasetSingleChart.vue'
import ChartCell from '@/components/commons/ChartCell.vue'
import DashboardShell from '@/components/commons/DashboardShell.vue'
import { BRACE_KEY, BRACE_SOURCE, PARALLEL_FIELDS, fetchBraces } from '@/components/braces/data'
import type { DoubleFields } from '@/composables/chart'
import { useDashboard } from '@/composables/dashboard'
import { useAutoFilters } from '@/composables/useAutoFilters'
import { useCountsStore } from '@/stores/counts'
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const { clickTableRow, closeDetail, item, query, search, searches, changeSearches } =
  useDashboard<BraceModel>(route, router, BraceField, {
    key: BRACE_KEY,
    fetchAll: fetchBraces
  })

const countsStore = useCountsStore()
onMounted(() => countsStore.fetch())

const parallelFields = PARALLEL_FIELDS

const parallelFilterFields: string[] = [
  BraceField.Id,
  ...parallelFields.flatMap((f) =>
    typeof f.id === 'string'
      ? [f.id]
      : 'dividend' in f.id
      ? [`${f.id.dividend}/${f.id.divisor}`]
      : []
  )
]
const boundaryConditionFields: DoubleFields<BraceField> = [
  BraceField.Date,
  BraceField.BoundaryCondition
]

// Filters are derived from the data dictionary + the loaded dataset, so a new
// column becomes filterable without touching this file, and fieldGroups.ts
// decides which category of the rail it shows up under.
const {
  filters,
  groups: filterGroups,
  loading: filtersLoading
} = useAutoFilters({
  database: 'braces',
  datasetKey: BRACE_KEY,
  fetchAll: fetchBraces,
  i18nPrefix: 'brace.'
})
</script>

<template>
  <dashboard-shell
    v-model:search="search"
    :eyebrow="$t('dashboards.common.eyebrow_components')"
    :title="$t('dashboards.brace.title')"
    :count="countsStore.counts.braces"
    :description="$t('dashboards.brace.description')"
    database-id="braces"
    i18n-prefix="brace."
    :filters="filters"
    :filter-groups="filterGroups"
    :filters-loading="filtersLoading"
    :searches="searches"
    :detail-open="!!item"
    @change:searches="changeSearches"
    @close:detail="closeDetail"
  >
    <template #table>
      <brace-table
        v-model:search="search"
        v-model:searches="searches"
        :query="query"
        @click:row="clickTableRow"
      />
    </template>

    <template #charts>
      <div class="charts-strip">
        <chart-cell
          :title="$t('dashboards.brace.chart_tests_per_year_bc')"
          :hint="$t('dashboards.common.hint_click_legend_to_filter')"
          :field="boundaryConditionFields"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <dataset-double-chart
            :source="BRACE_SOURCE"
            :fields="boundaryConditionFields"
            type="line"
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell
          quiet
          :title="$t('dashboards.brace.chart_loading_protocol')"
          :hint="$t('dashboards.common.hint_click_to_filter')"
          :field="BraceField.LoadingProtocol"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <dataset-single-chart
            :source="BRACE_SOURCE"
            :field="BraceField.LoadingProtocol"
            :show-reset="false"
            flat
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell
          quiet
          :title="$t('dashboards.brace.chart_steel_grade')"
          :hint="$t('dashboards.common.hint_click_to_filter')"
          :field="BraceField.Steel"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <dataset-single-chart
            :source="BRACE_SOURCE"
            :field="BraceField.Steel"
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
          <dataset-parallel-chart
            :source="BRACE_SOURCE"
            :fields="parallelFields"
            @change:searches="changeSearches"
          />
        </chart-cell>
      </div>
    </template>

    <template #detail>
      <brace-detail v-if="item" :brace="item" @close="closeDetail" />
    </template>
  </dashboard-shell>
</template>
