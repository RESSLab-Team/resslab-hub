<script setup lang="ts">
import { TensileCouponField, type TensileCouponModel } from '@/backend'
import ChartCell from '@/components/commons/ChartCell.vue'
import DashboardShell from '@/components/commons/DashboardShell.vue'
import type { FilterRailGroup } from '@/components/commons/FilterRail.vue'
import TensileCouponDoubleChart from '@/components/tensile-coupons/charts/TensileCouponDoubleChart.vue'
import TensileCouponParallelChart from '@/components/tensile-coupons/charts/TensileCouponParallelChart.vue'
import TensileCouponSingleChart from '@/components/tensile-coupons/charts/TensileCouponSingleChart.vue'
import TensileCouponDetail from '@/components/tensile-coupons/TensileCouponDetail.vue'
import TensileCouponTable from '@/components/tensile-coupons/TensileCouponTable.vue'
import type { DoubleFields, ParallelField } from '@/composables/chart'
import { useDashboard } from '@/composables/dashboard'
import { useCountsStore } from '@/stores/counts'
import { mauve, mint, sky } from '@/utils/vuetify'
import { mdiCalendarRange, mdiPulse, mdiTune } from '@mdi/js'
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

const { t } = useI18n({ useScope: 'global' })

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
const profileYearFields: DoubleFields<TensileCouponField> = [
  TensileCouponField.Year,
  TensileCouponField.ProfileType
]
const profileThicknessFields: DoubleFields<TensileCouponField> = [
  TensileCouponField.AvgInitReducedThicknessMm,
  TensileCouponField.ProfileType
]

const railGroups = computed<FilterRailGroup[]>(() => [
  {
    key: TensileCouponField.Year,
    label: t('dashboards.tensile_coupon.rail_test_year'),
    icon: mdiCalendarRange,
    type: 'range',
    min: 1970,
    max: 2026
  },
  {
    key: TensileCouponField.YieldStress02Mpa,
    label: t('dashboards.tensile_coupon.rail_yield_stress'),
    icon: mdiPulse,
    type: 'range'
  },
  {
    key: TensileCouponField.ElongationAtFracture,
    label: t('dashboards.tensile_coupon.rail_elongation_at_fracture'),
    icon: mdiTune,
    type: 'range'
  },
  {
    key: TensileCouponField.ReductionOfArea,
    label: t('dashboards.tensile_coupon.rail_reduction_of_area'),
    icon: mdiTune,
    type: 'range'
  },
  {
    key: TensileCouponField.AvgInitReducedThicknessMm,
    label: t('dashboards.tensile_coupon.rail_thickness'),
    icon: mdiTune,
    type: 'range'
  }
])
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
    :rail-groups="railGroups"
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
        <chart-cell>
          <tensile-coupon-parallel-chart
            :color="mint"
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
