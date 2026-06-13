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
const profileYearFields: DoubleFields<TensileCouponField> = [
  TensileCouponField.Year,
  TensileCouponField.ProfileType
]
const profileThicknessFields: DoubleFields<TensileCouponField> = [
  TensileCouponField.AvgInitReducedThicknessMm,
  TensileCouponField.ProfileType
]

const railGroups: FilterRailGroup[] = [
  {
    key: TensileCouponField.Year,
    label: 'Test year',
    icon: mdiCalendarRange,
    type: 'range',
    min: 1970,
    max: 2026
  },
  {
    key: TensileCouponField.YieldStress02Mpa,
    label: 'Yield stress (0.2%) [MPa]',
    icon: mdiPulse,
    type: 'range'
  },
  {
    key: TensileCouponField.ElongationAtFracture,
    label: 'Elongation at fracture',
    icon: mdiTune,
    type: 'range'
  },
  {
    key: TensileCouponField.ReductionOfArea,
    label: 'Reduction of area',
    icon: mdiTune,
    type: 'range'
  },
  {
    key: TensileCouponField.AvgInitReducedThicknessMm,
    label: 'Thickness [mm]',
    icon: mdiTune,
    type: 'range'
  }
]
</script>

<template>
  <dashboard-shell
    v-model:search="search"
    eyebrow="Materials · Database"
    title="Tensile Coupons"
    :count="countsStore.counts.tensile"
    count-label="coupons"
    description="Monotonic tensile coupon tests on structural steels, with engineering
      stress-strain curves and standardized mechanical properties. Filter through the filters
      panel, the table column filters or the charts below; click a row for the full coupon
      detail and digitized stress-strain data."
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
        <chart-cell quiet title="Steel grade" hint="Click to filter">
          <tensile-coupon-single-chart
            :color="sky"
            :field="TensileCouponField.SteelGrade"
            :query="query"
            :show-reset="false"
            flat
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell title="Coupons per year × profile type" hint="Click legend to filter">
          <tensile-coupon-double-chart
            :color="mint"
            :fields="profileYearFields"
            :query="query"
            type="line"
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell title="Thickness × profile type" hint="Stacked histogram · click bar or legend">
          <tensile-coupon-double-chart
            :color="mauve"
            :fields="profileThicknessFields"
            :query="query"
            type="bar"
            @change:searches="changeSearches"
          />
        </chart-cell>
      </div>

      <div class="charts-strip charts-strip-1col">
        <chart-cell>
          <tensile-coupon-parallel-chart
            :color="mint"
            :fields="parallelFields"
            :query="query"
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
