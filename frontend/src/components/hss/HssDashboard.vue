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
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

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

const railGroups: FilterRailGroup[] = [
  {
    key: HSSColumnField.Date,
    label: 'Test date',
    icon: mdiCalendarRange,
    type: 'range',
    min: 1970,
    max: 2026
  },
  {
    key: HSSColumnField.DepthOverT,
    label: 'Depth-to-thickness D/t',
    icon: mdiTune,
    type: 'range'
  },
  {
    key: HSSColumnField.AxialLoadRatio,
    label: 'Axial load ratio Pg/Py',
    icon: mdiPulse,
    type: 'range'
  },
  {
    key: HSSColumnField.LoadingAngle,
    label: 'Loading angle [°]',
    icon: mdiTune,
    type: 'range'
  },
  {
    key: HSSColumnField.FlexuralBuckling,
    label: 'Failure mode',
    icon: mdiTagOutline,
    type: 'chips',
    options: [
      { label: 'Local buckling', value: 'false' },
      { label: 'Flexural buckling', value: 'true' }
    ]
  }
]
</script>

<template>
  <dashboard-shell
    v-model:search="search"
    eyebrow="Components · Database"
    title="HSS Columns"
    :count="countsStore.counts.hss"
    description="Hollow structural section column tests under combined axial load and cyclic
      lateral loading, covering a range of depth-to-thickness ratios and loading angles. Filter
      through the filters panel, the table column filters or the charts below; click a row for
      the full specimen detail and digitized test data."
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
        <chart-cell quiet title="Loading protocol" hint="Click to filter">
          <hss-single-chart
            :color="yellowgreen"
            :field="HSSColumnField.LoadingProtocol"
            :query="query"
            :show-reset="false"
            flat
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell title="Tests per year × failure mode" hint="Click legend to filter">
          <hss-double-chart
            :color="periwinkle"
            :fields="failureModeFields"
            :query="query"
            type="line"
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell quiet title="Steel grade" hint="Click to filter">
          <hss-single-chart
            :color="plum"
            :field="HSSColumnField.SteelType"
            :query="query"
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
            :query="query"
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
