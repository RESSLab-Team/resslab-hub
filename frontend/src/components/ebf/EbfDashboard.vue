<script setup lang="ts">
import { EccentricBracedFrameField, type EccentricBracedFrameModel } from '@/backend'
import ChartCell from '@/components/commons/ChartCell.vue'
import DashboardShell from '@/components/commons/DashboardShell.vue'
import EbfDoubleChart from '@/components/ebf/charts/EbfDoubleChart.vue'
import EbfParallelChart from '@/components/ebf/charts/EbfParallelChart.vue'
import EbfSingleChart from '@/components/ebf/charts/EbfSingleChart.vue'
import EbfDetail from '@/components/ebf/EbfDetail.vue'
import EbfTable from '@/components/ebf/EbfTable.vue'
import type { DoubleFields, ParallelField } from '@/composables/chart'
import { EBF_KEY, fetchEbfs } from '@/components/ebf/data'
import { useDashboard } from '@/composables/dashboard'
import { useAutoFilters } from '@/composables/useAutoFilters'
import { useCountsStore } from '@/stores/counts'
import { sectionTypeMapping } from '@/utils/ebf'
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const { clickTableRow, closeDetail, item, query, search, searches, changeSearches } =
  useDashboard<EccentricBracedFrameModel>(route, router, EccentricBracedFrameField, {
    key: EBF_KEY,
    fetchAll: fetchEbfs
  })

const countsStore = useCountsStore()
onMounted(() => countsStore.fetch())

const parallelFields: ParallelField<EccentricBracedFrameField>[] = [
  { id: EccentricBracedFrameField.E, name: 'e [mm]' },
  { id: EccentricBracedFrameField.LinkLoc, name: 'Location' },
  { id: EccentricBracedFrameField.SecType, name: 'Type' },
  { id: EccentricBracedFrameField.SgFlgLink, name: 'Material' },
  { id: EccentricBracedFrameField.OvAisc, name: 'Ω' },
  {
    id: EccentricBracedFrameField.ClassAisc,
    name: 'Link Classification',
    sortValues: ['long', 'intermediate', 'short']
  }
]

const parallelFilterFields: string[] = [
  EccentricBracedFrameField.Id,
  ...parallelFields.flatMap((f) =>
    typeof f.id === 'string'
      ? [f.id]
      : 'dividend' in f.id
      ? [`${f.id.dividend}/${f.id.divisor}`]
      : []
  )
]
const yearSectionFields: DoubleFields<EccentricBracedFrameField> = [
  EccentricBracedFrameField.Year,
  {
    id: EccentricBracedFrameField.SecType,
    mapping: sectionTypeMapping
  }
]
const yearLinkFields: DoubleFields<EccentricBracedFrameField> = [
  EccentricBracedFrameField.Year,
  {
    id: EccentricBracedFrameField.ClassAisc,
    mapping: sectionTypeMapping
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
  database: 'ebf',
  datasetKey: EBF_KEY,
  fetchAll: fetchEbfs,
  i18nPrefix: 'ebf.'
})
</script>

<template>
  <dashboard-shell
    v-model:search="search"
    :eyebrow="$t('dashboards.common.eyebrow_components')"
    :title="$t('dashboards.ebf.title')"
    :count="countsStore.counts.ebf"
    :description="$t('dashboards.ebf.description')"
    database-id="ebf"
    i18n-prefix="ebf."
    :filters="filters"
    :filter-groups="filterGroups"
    :filters-loading="filtersLoading"
    :searches="searches"
    :detail-open="!!item"
    @change:searches="changeSearches"
    @close:detail="closeDetail"
  >
    <template #table>
      <ebf-table
        v-model:search="search"
        v-model:searches="searches"
        :query="query"
        @click:row="clickTableRow"
      />
    </template>

    <template #charts>
      <div class="charts-strip charts-strip-2cols">
        <chart-cell
          :title="$t('dashboards.ebf.chart_tests_per_year_section')"
          :hint="$t('dashboards.common.hint_click_legend_to_filter')"
          :field="yearSectionFields"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <ebf-double-chart
            :fields="yearSectionFields"
            type="line"
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell
          :title="$t('dashboards.ebf.chart_tests_per_year_classification')"
          :hint="$t('dashboards.common.hint_click_legend_to_filter')"
          :field="yearLinkFields"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <ebf-double-chart
            :fields="yearLinkFields"
            type="line"
            @change:searches="changeSearches"
          />
        </chart-cell>
      </div>

      <div class="charts-strip">
        <chart-cell
          quiet
          :title="$t('dashboards.ebf.chart_loading_protocol')"
          :hint="$t('dashboards.common.hint_click_to_filter')"
          :field="EccentricBracedFrameField.LPTyp"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <ebf-single-chart
            :field="EccentricBracedFrameField.LPTyp"
            :show-reset="false"
            flat
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell
          quiet
          :title="$t('dashboards.ebf.chart_test_configuration')"
          :hint="$t('dashboards.common.hint_click_to_filter')"
          :field="EccentricBracedFrameField.LConfi"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <ebf-single-chart
            :field="EccentricBracedFrameField.LConfi"
            :show-reset="false"
            flat
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell
          quiet
          :title="$t('dashboards.ebf.chart_steel_grade')"
          :hint="$t('dashboards.common.hint_click_to_filter')"
          :field="EccentricBracedFrameField.SgFlgLink"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <ebf-single-chart
            :field="EccentricBracedFrameField.SgFlgLink"
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
          <ebf-parallel-chart :fields="parallelFields" @change:searches="changeSearches" />
        </chart-cell>
      </div>
    </template>

    <template #detail>
      <ebf-detail v-if="item" :eccentric-braced-frame="item" @close="closeDetail" />
    </template>
  </dashboard-shell>
</template>
