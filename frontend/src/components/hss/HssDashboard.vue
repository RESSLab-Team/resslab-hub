<script setup lang="ts">
import { HSSColumnField, type HSSColumnModel } from '@/backend'
import ChartCell from '@/components/commons/ChartCell.vue'
import DashboardShell from '@/components/commons/DashboardShell.vue'
import DatasetDoubleChart from '@/components/commons/charts/DatasetDoubleChart.vue'
import DatasetParallelChart from '@/components/commons/charts/DatasetParallelChart.vue'
import DatasetSingleChart from '@/components/commons/charts/DatasetSingleChart.vue'
import HssDetail from '@/components/hss/HssDetail.vue'
import HssTable from '@/components/hss/HssTable.vue'
import {
  HSS_KEY,
  HSS_SOURCE,
  fetchHsss,
  parallelFields as buildParallelFields
} from '@/components/hss/data'
import type { DoubleFields } from '@/composables/chart'
import { useDashboard } from '@/composables/dashboard'
import { useAutoFilters } from '@/composables/useAutoFilters'
import { useCountsStore } from '@/stores/counts'
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const { clickTableRow, closeDetail, item, query, search, searches, changeSearches } =
  useDashboard<HSSColumnModel>(route, router, HSSColumnField, {
    key: HSS_KEY,
    fetchAll: fetchHsss
  })

const countsStore = useCountsStore()
onMounted(() => countsStore.fetch())

// Computed, so the configuration labels follow a language switch.
const parallelFields = computed(() => buildParallelFields())

const parallelFilterFields: string[] = [
  HSSColumnField.Id,
  ...buildParallelFields().flatMap((f) =>
    typeof f.id === 'string'
      ? [f.id]
      : 'dividend' in f.id
      ? [`${f.id.dividend}/${f.id.divisor}`]
      : []
  )
]
const failureModeFields: DoubleFields<HSSColumnField> = [
  HSSColumnField.Date,
  {
    id: HSSColumnField.FlexuralBuckling,
    mapping: new Map([
      ['FALSE', 'Local Buckling'],
      ['TRUE', 'Flexural Buckling']
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
  database: 'hss',
  datasetKey: HSS_KEY,
  fetchAll: fetchHsss,
  i18nPrefix: 'hss.'
})
</script>

<template>
  <dashboard-shell
    v-model:search="search"
    :eyebrow="$t('dashboards.common.eyebrow_components')"
    :title="$t('dashboards.hss.title')"
    :count="countsStore.counts.hss"
    :description="$t('dashboards.hss.description')"
    database-id="hss"
    i18n-prefix="hss."
    :filters="filters"
    :filter-groups="filterGroups"
    :filters-loading="filtersLoading"
    :searches="searches"
    :detail-open="!!item"
    @change:searches="changeSearches"
    @close:detail="closeDetail"
  >
    <template #table>
      <hss-table
        v-model:search="search"
        v-model:searches="searches"
        :query="query"
        @click:row="clickTableRow"
      />
    </template>

    <template #charts>
      <div class="charts-strip">
        <chart-cell
          :title="$t('dashboards.hss.chart_tests_per_year_failure_mode')"
          :hint="$t('dashboards.common.hint_click_legend_to_filter')"
          :field="failureModeFields"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <dataset-double-chart
            :source="HSS_SOURCE"
            :fields="failureModeFields"
            type="line"
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell
          quiet
          :title="$t('dashboards.hss.chart_loading_protocol')"
          :hint="$t('dashboards.common.hint_click_to_filter')"
          :field="HSSColumnField.LoadingProtocol"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <dataset-single-chart
            :source="HSS_SOURCE"
            :field="HSSColumnField.LoadingProtocol"
            :show-reset="false"
            flat
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell
          quiet
          :title="$t('dashboards.hss.chart_steel_grade')"
          :hint="$t('dashboards.common.hint_click_to_filter')"
          :field="HSSColumnField.SteelType"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <dataset-single-chart
            :source="HSS_SOURCE"
            :field="HSSColumnField.SteelType"
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
            :source="HSS_SOURCE"
            :fields="parallelFields"
            @change:searches="changeSearches"
          />
        </chart-cell>
      </div>
    </template>

    <template #detail>
      <hss-detail v-if="item" :hss-column="item" @close="closeDetail" />
    </template>
  </dashboard-shell>
</template>
