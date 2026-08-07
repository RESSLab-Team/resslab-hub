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
import { PARALLEL_FIELDS } from '@/components/columns/data'
import type { DoubleFields } from '@/composables/chart'
import { useDashboard } from '@/composables/dashboard'
import { useCountsStore } from '@/stores/counts'
import { cobalt, mint, plum } from '@/utils/vuetify'
import { mdiCalendarRange, mdiPulse, mdiTagOutline, mdiTune } from '@mdi/js'
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

const { t } = useI18n({ useScope: 'global' })

const route = useRoute()
const router = useRouter()
const { clickTableRow, closeDetail, item, query, search, searches, changeSearches, updatePage } =
  useDashboard<ColumnModel>(route, router, ColumnField)

const countsStore = useCountsStore()
onMounted(() => countsStore.fetch())

const parallelFields = PARALLEL_FIELDS

const parallelFilterFields: string[] = [
  ColumnField.Id,
  ...parallelFields.flatMap((f) =>
    typeof f.id === 'string'
      ? [f.id]
      : 'dividend' in f.id
      ? [`${f.id.dividend}/${f.id.divisor}`]
      : []
  )
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

const railGroups = computed<FilterRailGroup[]>(() => [
  {
    key: ColumnField.Date,
    label: t('dashboards.column.rail_test_date'),
    icon: mdiCalendarRange,
    type: 'range',
    min: 1960,
    max: 2026
  },
  {
    key: ColumnField.BuiltUp,
    label: t('dashboards.column.rail_fabrication'),
    icon: mdiTagOutline,
    type: 'chips',
    options: [
      { label: 'Hot-rolled', value: 'false' },
      { label: 'Built-up', value: 'true' }
    ]
  },
  {
    key: ColumnField.DC,
    label: t('dashboards.column.rail_column_depth'),
    icon: mdiTune,
    type: 'range'
  },
  {
    key: ColumnField.PGOverPYm,
    label: t('dashboards.column.rail_axial_load_ratio'),
    icon: mdiPulse,
    type: 'range'
  },
  {
    key: ColumnField.LBOverRYc,
    label: t('dashboards.column.rail_slenderness'),
    icon: mdiTune,
    type: 'range'
  }
])
</script>

<template>
  <dashboard-shell
    v-model:search="search"
    :eyebrow="$t('dashboards.common.eyebrow_components')"
    :title="$t('dashboards.column.title')"
    :count="countsStore.counts.columns"
    :description="$t('dashboards.column.description')"
    database-id="columns"
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
        <chart-cell
          :title="$t('dashboards.column.chart_tests_per_year_bc')"
          :hint="$t('dashboards.common.hint_click_legend_to_filter')"
          :field="boundaryConditionFields"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <column-double-chart
            :color="mint"
            :fields="boundaryConditionFields"
            type="line"
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell
          :title="$t('dashboards.column.chart_column_depth_fabrication')"
          :hint="$t('dashboards.common.hint_stacked_histogram')"
          :field="columnDepthFields"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <column-double-chart
            :color="cobalt"
            :fields="columnDepthFields"
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell
          quiet
          :title="$t('dashboards.column.chart_steel_grade')"
          :hint="$t('dashboards.common.hint_click_to_filter')"
          :field="ColumnField.SteelC"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <column-single-chart
            :color="plum"
            :field="ColumnField.SteelC"
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
          <column-parallel-chart :fields="parallelFields" @change:searches="changeSearches" />
        </chart-cell>
      </div>
    </template>

    <template #detail>
      <column-detail v-if="item" :column="item" @close="closeDetail" />
    </template>
  </dashboard-shell>
</template>
