<script setup lang="ts">
import { MaterialField, type MaterialModel } from '@/backend'
import ChartCell from '@/components/commons/ChartCell.vue'
import DashboardShell from '@/components/commons/DashboardShell.vue'
import type { FilterRailGroup } from '@/components/commons/FilterRail.vue'
import MaterialDoubleChart from '@/components/materials/charts/MaterialDoubleChart.vue'
import MaterialParallelChart from '@/components/materials/charts/MaterialParallelChart.vue'
import MaterialSingleChart from '@/components/materials/charts/MaterialSingleChart.vue'
import MaterialDetail from '@/components/materials/MaterialDetail.vue'
import MaterialTable from '@/components/materials/MaterialTable.vue'
import type { DoubleFields, ParallelField } from '@/composables/chart'
import { useDashboard } from '@/composables/dashboard'
import { useCountsStore } from '@/stores/counts'
import { apricot, periwinkle, plum } from '@/utils/vuetify'
import { mdiCalendarRange, mdiPulse, mdiTune } from '@mdi/js'
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

const { t } = useI18n({ useScope: 'global' })

const route = useRoute()
const router = useRouter()
const { clickTableRow, closeDetail, item, query, search, searches, changeSearches, updatePage } =
  useDashboard<MaterialModel>(route, router, MaterialField)

const countsStore = useCountsStore()
onMounted(() => countsStore.fetch())

const parallelFields: ParallelField<MaterialField>[] = [
  { id: MaterialField.Type },
  { id: MaterialField.YieldStressMpa },
  {
    id: {
      dividend: MaterialField.YieldStressMpa,
      divisor: MaterialField.FyNMpa
    }
  },
  { id: MaterialField.FractureStrain },
  { id: MaterialField.Thickness }
]
const profileFields: DoubleFields<MaterialField> = [MaterialField.Year, MaterialField.ProfileType]
const profileThicknessFields: DoubleFields<MaterialField> = [
  MaterialField.Thickness,
  MaterialField.ProfileType
]

const railGroups = computed<FilterRailGroup[]>(() => [
  {
    key: MaterialField.Year,
    label: t('dashboards.material.rail_test_year'),
    icon: mdiCalendarRange,
    type: 'range',
    min: 1970,
    max: 2026
  },
  {
    key: MaterialField.YieldStressMpa,
    label: t('dashboards.material.rail_yield_stress'),
    icon: mdiPulse,
    type: 'range'
  },
  {
    key: MaterialField.FractureStrain,
    label: t('dashboards.material.rail_fracture_strain'),
    icon: mdiTune,
    type: 'range'
  },
  {
    key: MaterialField.Thickness,
    label: t('dashboards.material.rail_thickness'),
    icon: mdiTune,
    type: 'range'
  }
])
</script>

<template>
  <dashboard-shell
    v-model:search="search"
    :eyebrow="$t('dashboards.common.eyebrow_materials')"
    :title="$t('dashboards.material.title')"
    :count="countsStore.counts.cyclic"
    count-label="coupons"
    :description="$t('dashboards.material.description')"
    i18n-prefix="material."
    :rail-groups="railGroups"
    :searches="searches"
    :detail-open="!!item"
    @change:searches="changeSearches"
    @close:detail="closeDetail"
  >
    <template #table>
      <material-table
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
          quiet
          :title="$t('dashboards.material.chart_steel_type')"
          :hint="$t('dashboards.common.hint_click_to_filter')"
          :field="MaterialField.Type"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <material-single-chart
            :color="plum"
            :field="MaterialField.Type"
            :query="query"
            :show-reset="false"
            flat
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell
          :title="$t('dashboards.material.chart_coupons_per_year_profile')"
          :hint="$t('dashboards.common.hint_click_legend_to_filter')"
          :field="profileFields"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <material-double-chart
            :color="periwinkle"
            :fields="profileFields"
            :query="query"
            type="line"
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell
          :title="$t('dashboards.material.chart_thickness_profile')"
          :hint="$t('dashboards.common.hint_stacked_histogram')"
          :field="profileThicknessFields"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <material-double-chart
            :color="apricot"
            :fields="profileThicknessFields"
            :query="query"
            type="bar"
            @change:searches="changeSearches"
          />
        </chart-cell>
      </div>

      <div class="charts-strip charts-strip-1col">
        <chart-cell>
          <material-parallel-chart
            :color="plum"
            :fields="parallelFields"
            :query="query"
            @change:searches="changeSearches"
          />
        </chart-cell>
      </div>
    </template>

    <template #detail>
      <material-detail v-if="item" :material="item" @close="closeDetail" />
    </template>
  </dashboard-shell>
</template>
