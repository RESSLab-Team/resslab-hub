<script setup lang="ts">
import { TensileCouponField, type TensileCouponModel } from '@/backend'
import ChartCell from '@/components/commons/ChartCell.vue'
import DashboardShell from '@/components/commons/DashboardShell.vue'
import TensileCouponDoubleChart from '@/components/tensile-coupons/charts/TensileCouponDoubleChart.vue'
import TensileCouponParallelChart from '@/components/tensile-coupons/charts/TensileCouponParallelChart.vue'
import TensileCouponSingleChart from '@/components/tensile-coupons/charts/TensileCouponSingleChart.vue'
import TensileCouponDetail from '@/components/tensile-coupons/TensileCouponDetail.vue'
import TensileCouponTable from '@/components/tensile-coupons/TensileCouponTable.vue'
import type { DoubleFields, ParallelField } from '@/composables/chart'
import { TENSILE_COUPON_KEY, fetchTensileCoupons } from '@/components/tensile-coupons/data'
import { useDashboard } from '@/composables/dashboard'
import { useAutoFilters } from '@/composables/useAutoFilters'
import { useCountsStore } from '@/stores/counts'
import { mauve, mint, sky } from '@/utils/vuetify'
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const { clickTableRow, closeDetail, item, query, search, searches, changeSearches, updatePage } =
  useDashboard<TensileCouponModel>(route, router, TensileCouponField)

const countsStore = useCountsStore()
onMounted(() => countsStore.fetch())

const parallelFields: ParallelField<TensileCouponField>[] = [
  { id: TensileCouponField.SteelGrade },
  { id: TensileCouponField.YieldStress02Mpa },
  {
    id: {
      dividend: TensileCouponField.TensileStrengthMpa,
      divisor: TensileCouponField.YieldStress02Mpa
    }
  },
  {
    id: {
      dividend: TensileCouponField.YieldStress02Mpa,
      divisor: TensileCouponField.FyNMpa
    }
  },
  { id: TensileCouponField.ElongationAtFracture },
  { id: TensileCouponField.ReductionOfArea },
  { id: TensileCouponField.AvgInitReducedThicknessMm }
]

const parallelFilterFields: string[] = [
  TensileCouponField.Id,
  ...parallelFields.flatMap((f) =>
    typeof f.id === 'string'
      ? [f.id]
      : 'dividend' in f.id
      ? [`${f.id.dividend}/${f.id.divisor}`]
      : []
  )
]
const profileYearFields: DoubleFields<TensileCouponField> = [
  TensileCouponField.Year,
  TensileCouponField.ProfileType
]
const profileThicknessFields: DoubleFields<TensileCouponField> = [
  TensileCouponField.AvgInitReducedThicknessMm,
  TensileCouponField.ProfileType
]

// Filters are derived from the data dictionary + the loaded dataset, so a new
// column becomes filterable without touching this file, and fieldGroups.ts
// decides which category of the rail it shows up under.
const {
  filters,
  groups: filterGroups,
  loading: filtersLoading
} = useAutoFilters({
  database: 'tensile',
  datasetKey: TENSILE_COUPON_KEY,
  fetchAll: fetchTensileCoupons,
  i18nPrefix: 'tensile_coupon.'
})
</script>

<template>
  <dashboard-shell
    v-model:search="search"
    :eyebrow="$t('dashboards.common.eyebrow_materials')"
    :title="$t('dashboards.tensile_coupon.title')"
    :count="countsStore.counts.tensile"
    count-label="coupons"
    :description="$t('dashboards.tensile_coupon.description')"
    database-id="tensile"
    i18n-prefix="tensile_coupon."
    :filters="filters"
    :filter-groups="filterGroups"
    :filters-loading="filtersLoading"
    :searches="searches"
    :detail-open="!!item"
    @change:searches="changeSearches"
    @close:detail="closeDetail"
  >
    <template #table>
      <tensile-coupon-table
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
          :title="$t('dashboards.tensile_coupon.chart_coupons_per_year_profile')"
          :hint="$t('dashboards.common.hint_click_legend_to_filter')"
          :field="profileYearFields"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <tensile-coupon-double-chart
            :color="mint"
            :fields="profileYearFields"
            type="line"
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell
          :title="$t('dashboards.tensile_coupon.chart_thickness_profile')"
          :hint="$t('dashboards.common.hint_stacked_histogram')"
          :field="profileThicknessFields"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <tensile-coupon-double-chart
            :color="mauve"
            :fields="profileThicknessFields"
            type="bar"
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell
          quiet
          :title="$t('dashboards.tensile_coupon.chart_steel_grade')"
          :hint="$t('dashboards.common.hint_click_to_filter')"
          :field="TensileCouponField.SteelGrade"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <tensile-coupon-single-chart
            :color="sky"
            :field="TensileCouponField.SteelGrade"
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
          <tensile-coupon-parallel-chart
            :fields="parallelFields"
            @change:searches="changeSearches"
          />
        </chart-cell>
      </div>
    </template>

    <template #detail>
      <tensile-coupon-detail v-if="item" :tensile-coupon="item" @close="closeDetail" />
    </template>
  </dashboard-shell>
</template>
