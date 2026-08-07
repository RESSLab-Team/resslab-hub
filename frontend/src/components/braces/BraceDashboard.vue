<script setup lang="ts">
import { BraceField, type BraceModel } from '@/backend'
import BraceDetail from '@/components/braces/BraceDetail.vue'
import BraceTable from '@/components/braces/BraceTable.vue'
import BraceDoubleChart from '@/components/braces/charts/BraceDoubleChart.vue'
import BraceParallelChart from '@/components/braces/charts/BraceParallelChart.vue'
import BraceSingleChart from '@/components/braces/charts/BraceSingleChart.vue'
import ChartCell from '@/components/commons/ChartCell.vue'
import DashboardShell from '@/components/commons/DashboardShell.vue'
import type { FilterRailGroup } from '@/components/commons/FilterRail.vue'
import { PARALLEL_FIELDS } from '@/components/braces/data'
import type { DoubleFields } from '@/composables/chart'
import { useDashboard } from '@/composables/dashboard'
import { useCountsStore } from '@/stores/counts'
import { apricot, mauve, sky } from '@/utils/vuetify'
import { mdiCalendarRange, mdiPulse, mdiTune } from '@mdi/js'
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

const { t } = useI18n({ useScope: 'global' })

const route = useRoute()
const router = useRouter()
const { clickTableRow, closeDetail, item, query, search, searches, changeSearches, updatePage } =
  useDashboard<BraceModel>(route, router, BraceField)

const countsStore = useCountsStore()
onMounted(() => countsStore.fetch())

const parallelFields = PARALLEL_FIELDS

const parallelFilterFields: string[] = [
  BraceField.Id,
  ...parallelFields.flatMap((f) =>
    typeof f.id === 'string'
      ? [f.id]
      : 'dividend' in f.id
      ? [`${f.id.dividend}/${f.id.divisor}`]
      : []
  )
]
const boundaryConditionFields: DoubleFields<BraceField> = [
  BraceField.Date,
  BraceField.BoundaryCondition
]

const railGroups = computed<FilterRailGroup[]>(() => [
  {
    key: BraceField.Date,
    label: t('dashboards.brace.rail_test_date'),
    icon: mdiCalendarRange,
    type: 'range',
    min: 1970,
    max: 2026
  },
  {
    key: BraceField.KlR,
    label: t('dashboards.brace.rail_slenderness'),
    icon: mdiPulse,
    type: 'range'
  },
  {
    key: BraceField.DBr,
    label: t('dashboards.brace.rail_section_depth'),
    icon: mdiTune,
    type: 'range'
  }
])
</script>

<template>
  <dashboard-shell
    v-model:search="search"
    :eyebrow="$t('dashboards.common.eyebrow_components')"
    :title="$t('dashboards.brace.title')"
    :count="countsStore.counts.braces"
    :description="$t('dashboards.brace.description')"
    database-id="braces"
    i18n-prefix="brace."
    :rail-groups="railGroups"
    :searches="searches"
    :detail-open="!!item"
    @change:searches="changeSearches"
    @close:detail="closeDetail"
  >
    <template #table>
      <brace-table
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
          :title="$t('dashboards.brace.chart_tests_per_year_bc')"
          :hint="$t('dashboards.common.hint_click_legend_to_filter')"
          :field="boundaryConditionFields"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <brace-double-chart
            :color="sky"
            :fields="boundaryConditionFields"
            type="line"
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell
          quiet
          :title="$t('dashboards.brace.chart_loading_protocol')"
          :hint="$t('dashboards.common.hint_click_to_filter')"
          :field="BraceField.LoadingProtocol"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <brace-single-chart
            :color="apricot"
            :field="BraceField.LoadingProtocol"
            :show-reset="false"
            flat
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell
          quiet
          :title="$t('dashboards.brace.chart_steel_grade')"
          :hint="$t('dashboards.common.hint_click_to_filter')"
          :field="BraceField.Steel"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <brace-single-chart
            :color="mauve"
            :field="BraceField.Steel"
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
          <brace-parallel-chart :fields="parallelFields" @change:searches="changeSearches" />
        </chart-cell>
      </div>
    </template>

    <template #detail>
      <brace-detail v-if="item" :brace="item" @close="closeDetail" />
    </template>
  </dashboard-shell>
</template>
