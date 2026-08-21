<script setup lang="ts">
import { ResidualStressField, type ResidualStressModel } from '@/backend'
import ChartCell from '@/components/commons/ChartCell.vue'
import DashboardShell from '@/components/commons/DashboardShell.vue'
import ResidualDoubleChart from '@/components/residuals/charts/ResidualDoubleChart.vue'
import ResidualParallelChart from '@/components/residuals/charts/ResidualParallelChart.vue'
import ResidualSingleChart from '@/components/residuals/charts/ResidualSingleChart.vue'
import ResidualDetail from '@/components/residuals/ResidualDetail.vue'
import ResidualTable from '@/components/residuals/ResidualTable.vue'
import { PARALLEL_FIELDS, RESIDUAL_KEY, fetchResiduals } from '@/components/residuals/data'
import type { DoubleFields } from '@/composables/chart'
import { useDashboard } from '@/composables/dashboard'
import { useAutoFilters } from '@/composables/useAutoFilters'
import { useCountsStore } from '@/stores/counts'
import { cobalt, peach, yellowgreen } from '@/utils/vuetify'
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const { clickTableRow, closeDetail, item, query, search, searches, changeSearches, updatePage } =
  useDashboard<ResidualStressModel>(route, router, ResidualStressField)

const countsStore = useCountsStore()
onMounted(() => countsStore.fetch())

const parallelFields = PARALLEL_FIELDS

const parallelFilterFields: string[] = [
  ResidualStressField.Id,
  ...parallelFields.flatMap((f) =>
    typeof f.id === 'string'
      ? [f.id]
      : 'dividend' in f.id
      ? [`${f.id.dividend}/${f.id.divisor}`]
      : []
  )
]
const profileFields: DoubleFields<ResidualStressField> = [
  ResidualStressField.Date,
  ResidualStressField.ProfileType
]

// Filters are derived from the data dictionary + the loaded dataset, so a new
// column becomes filterable without touching this file; `pinned` only keeps the
// long-standing filters at the top of the rail.
const { filters, loading: filtersLoading } = useAutoFilters({
  database: 'residuals',
  datasetKey: RESIDUAL_KEY,
  fetchAll: fetchResiduals,
  i18nPrefix: 'residual.',
  pinned: [
    ResidualStressField.Date,
    ResidualStressField.Tf,
    ResidualStressField.HOverB,
    ResidualStressField.Sigma0F,
    ResidualStressField.Sigma0W
  ]
})
</script>

<template>
  <dashboard-shell
    v-model:search="search"
    :eyebrow="$t('dashboards.common.eyebrow_materials')"
    :title="$t('dashboards.residual.title')"
    :count="countsStore.counts.residuals"
    count-label="specimens"
    :description="$t('dashboards.residual.description')"
    database-id="residuals"
    i18n-prefix="residual."
    :filters="filters"
    :filters-loading="filtersLoading"
    :searches="searches"
    :detail-open="!!item"
    @change:searches="changeSearches"
    @close:detail="closeDetail"
  >
    <template #table>
      <residual-table
        v-model:search="search"
        v-model:searches="searches"
        :query="query"
        @click:row="clickTableRow"
        @update:page="updatePage"
      />
    </template>

    <template #charts>
      <div class="charts-strip">
        <chart-cell
          :title="$t('dashboards.residual.chart_specimens_per_year_profile')"
          :hint="$t('dashboards.common.hint_click_legend_to_filter')"
          :field="profileFields"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <residual-double-chart
            :color="peach"
            :fields="profileFields"
            type="line"
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell
          :title="$t('dashboards.residual.chart_section_height_profile')"
          :hint="$t('dashboards.common.hint_stacked_histogram')"
          :field="[ResidualStressField.H, ResidualStressField.ProfileType]"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <residual-double-chart
            :color="yellowgreen"
            :fields="[ResidualStressField.H, ResidualStressField.ProfileType]"
            type="bar"
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell
          quiet
          :title="$t('dashboards.residual.chart_steel_grade')"
          :hint="$t('dashboards.common.hint_click_to_filter')"
          :field="ResidualStressField.Steel"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <residual-single-chart
            :color="cobalt"
            :field="ResidualStressField.Steel"
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
          <residual-parallel-chart :fields="parallelFields" @change:searches="changeSearches" />
        </chart-cell>
      </div>
    </template>

    <template #detail>
      <residual-detail v-if="item" :residual="item" @close="closeDetail" />
    </template>
  </dashboard-shell>
</template>
