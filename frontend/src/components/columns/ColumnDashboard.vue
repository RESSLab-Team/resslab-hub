<script setup lang="ts">
import { ColumnField, type ColumnModel } from '@/backend'
import ChartCell from '@/components/commons/ChartCell.vue'
import DashboardShell from '@/components/commons/DashboardShell.vue'
import type { FilterRailGroup } from '@/components/commons/FilterRail.vue'
import ColumnDoubleChart from '@/components/columns/charts/ColumnDoubleChart.vue'
import ColumnParallelChart from '@/components/columns/charts/ColumnParallelChart.vue'
import ColumnSingleChart from '@/components/columns/charts/ColumnSingleChart.vue'
import ColumnDetail from '@/components/columns/ColumnDetail.vue'
import ColumnTable from '@/components/columns/ColumnTable.vue'
import type { DoubleFields, ParallelField } from '@/composables/chart'
import { useDashboard } from '@/composables/dashboard'
import { useCountsStore } from '@/stores/counts'
import { cobalt, mint, plum } from '@/utils/vuetify'
import { mdiCalendarRange, mdiPulse, mdiTagOutline, mdiTune } from '@mdi/js'
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const { clickTableRow, closeDetail, item, query, search, searches, changeSearches, updatePage } =
  useDashboard<ColumnModel>(route, router, ColumnField)

const countsStore = useCountsStore()
onMounted(() => countsStore.fetch())

const parallelFields: ParallelField<ColumnField>[] = [
  { id: ColumnField.Th80 },
  { id: ColumnField.HOverTCw },
  { id: ColumnField.BFOverTCf },
  { id: ColumnField.LBOverRYc },
  { id: ColumnField.PGOverPYm }
]
const boundaryConditionFields: DoubleFields<ColumnField> = [
  ColumnField.Date,
  ColumnField.BoundaryCondition
]
const columnDepthFields: DoubleFields<ColumnField> = [
  ColumnField.DC,
  {
    id: ColumnField.BuiltUp,
    mapping: new Map([
      ['False', 'Hot Rolled'],
      ['True', 'Built Up']
    ])
  }
]

const railGroups: FilterRailGroup[] = [
  {
    key: ColumnField.Date,
    label: 'Test date',
    icon: mdiCalendarRange,
    type: 'range',
    min: 1960,
    max: 2026
  },
  {
    key: ColumnField.BuiltUp,
    label: 'Fabrication',
    icon: mdiTagOutline,
    type: 'chips',
    options: [
      { label: 'Hot-rolled', value: 'false' },
      { label: 'Built-up', value: 'true' }
    ]
  },
  {
    key: ColumnField.DC,
    label: 'Column depth dc [mm]',
    icon: mdiTune,
    type: 'range'
  },
  {
    key: ColumnField.PGOverPYm,
    label: 'Axial load ratio Pg/Py',
    icon: mdiPulse,
    type: 'range'
  },
  {
    key: ColumnField.LBOverRYc,
    label: 'Slenderness Lb/ry',
    icon: mdiTune,
    type: 'range'
  }
]
</script>

<template>
  <dashboard-shell
    v-model:search="search"
    eyebrow="Components · Database"
    title="Columns"
    :count="countsStore.counts.columns"
    description="Wide-flange steel column tests under combined axial load and cyclic lateral
      drift, covering hot-rolled and built-up sections. Filter through the filters panel, the
      table column filters or the charts below; click a row for the full specimen detail and
      digitized test data."
    i18n-prefix="column."
    :rail-groups="railGroups"
    :searches="searches"
    :detail-open="!!item"
    @change:searches="changeSearches"
    @close:detail="closeDetail"
  >
    <template #table>
      <column-table
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
          <column-single-chart
            :color="plum"
            :field="ColumnField.SteelC"
            :query="query"
            :show-reset="false"
            flat
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell title="Tests per year × boundary condition" hint="Click legend to filter">
          <column-double-chart
            :color="mint"
            :fields="boundaryConditionFields"
            :query="query"
            type="line"
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell
          title="Column depth × fabrication"
          hint="Stacked histogram · click bar or legend"
        >
          <column-double-chart
            :color="cobalt"
            :fields="columnDepthFields"
            :query="query"
            @change:searches="changeSearches"
          />
        </chart-cell>
      </div>

      <div class="charts-strip charts-strip-1col">
        <chart-cell>
          <column-parallel-chart
            :color="mint"
            :fields="parallelFields"
            :query="query"
            @change:searches="changeSearches"
          />
        </chart-cell>
      </div>
    </template>

    <template #detail>
      <column-detail v-if="item" :column="item" @close="closeDetail" />
    </template>
  </dashboard-shell>
</template>
