<script setup lang="ts">
import { HSSColumnField, type HSSColumnModel } from '@/backend'
import ChartCell from '@/components/commons/ChartCell.vue'
import DashboardShell from '@/components/commons/DashboardShell.vue'
import type { FilterRailGroup } from '@/components/commons/FilterRail.vue'
import HssDoubleChart from '@/components/hss/charts/HssDoubleChart.vue'
import HssParallelChart from '@/components/hss/charts/HssParallelChart.vue'
import HssSingleChart from '@/components/hss/charts/HssSingleChart.vue'
import HssDetail from '@/components/hss/HssDetail.vue'
import HssTable from '@/components/hss/HssTable.vue'
import type { DoubleFields, ParallelField } from '@/composables/chart'
import { useDashboard } from '@/composables/dashboard'
import { useCountsStore } from '@/stores/counts'
import { testConfigurationNameMapping } from '@/utils/hss'
import { periwinkle, plum, sky, yellowgreen } from '@/utils/vuetify'
import { mdiCalendarRange, mdiPulse, mdiTagOutline, mdiTune } from '@mdi/js'
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

const { t } = useI18n({ useScope: 'global' })

const route = useRoute()
const router = useRouter()
const { clickTableRow, closeDetail, item, query, search, searches, changeSearches, updatePage } =
  useDashboard<HSSColumnModel>(route, router, HSSColumnField)

const countsStore = useCountsStore()
onMounted(() => countsStore.fetch())

const parallelFields: ParallelField<HSSColumnField>[] = [
  { id: HSSColumnField.ThetaPPos100fitRad, name: 'θp [rad]' },
  { id: HSSColumnField.DepthOverT, name: 'D/t' },
  { id: HSSColumnField.AxialLoadRatio, name: 'Pg/Py' },
  { id: HSSColumnField.LoadingAngle, name: 'Load Angle [degrees]' },
  {
    id: HSSColumnField.TestConfiguration,
    name: 'Configuration',
    mapping: testConfigurationNameMapping
  }
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

const railGroups = computed<FilterRailGroup[]>(() => [
  {
    key: HSSColumnField.Date,
    label: t('dashboards.hss.rail_test_date'),
    icon: mdiCalendarRange,
    type: 'range',
    min: 1970,
    max: 2026
  },
  {
    key: HSSColumnField.DepthOverT,
    label: t('dashboards.hss.rail_depth_to_thickness'),
    icon: mdiTune,
    type: 'range'
  },
  {
    key: HSSColumnField.AxialLoadRatio,
    label: t('dashboards.hss.rail_axial_load_ratio'),
    icon: mdiPulse,
    type: 'range'
  },
  {
    key: HSSColumnField.LoadingAngle,
    label: t('dashboards.hss.rail_loading_angle'),
    icon: mdiTune,
    type: 'range'
  },
  {
    key: HSSColumnField.FlexuralBuckling,
    label: t('dashboards.hss.rail_failure_mode'),
    icon: mdiTagOutline,
    type: 'chips',
    options: [
      { label: 'Local buckling', value: 'false' },
      { label: 'Flexural buckling', value: 'true' }
    ]
  }
])
</script>

<template>
  <dashboard-shell
    v-model:search="search"
    :eyebrow="$t('dashboards.common.eyebrow_components')"
    :title="$t('dashboards.hss.title')"
    :count="countsStore.counts.hss"
    :description="$t('dashboards.hss.description')"
    i18n-prefix="hss."
    :rail-groups="railGroups"
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
        @update:page="updatePage"
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
          <hss-double-chart
            :color="periwinkle"
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
          <hss-single-chart
            :color="yellowgreen"
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
          <hss-single-chart
            :color="plum"
            :field="HSSColumnField.SteelType"
            :show-reset="false"
            flat
            @change:searches="changeSearches"
          />
        </chart-cell>
      </div>

      <div class="charts-strip charts-strip-1col">
        <chart-cell>
          <hss-parallel-chart
            :color="sky"
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
