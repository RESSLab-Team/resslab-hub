<script setup lang="ts">
import { ResidualStressField, type ResidualStressModel } from '@/backend'
import ChartCell from '@/components/commons/ChartCell.vue'
import DashboardShell from '@/components/commons/DashboardShell.vue'
import type { FilterRailGroup } from '@/components/commons/FilterRail.vue'
import ResidualDoubleChart from '@/components/residuals/charts/ResidualDoubleChart.vue'
import ResidualParallelChart from '@/components/residuals/charts/ResidualParallelChart.vue'
import ResidualSingleChart from '@/components/residuals/charts/ResidualSingleChart.vue'
import ResidualDetail from '@/components/residuals/ResidualDetail.vue'
import ResidualTable from '@/components/residuals/ResidualTable.vue'
import type { DoubleFields, ParallelField } from '@/composables/chart'
import { useDashboard } from '@/composables/dashboard'
import { useCountsStore } from '@/stores/counts'
import { cobalt, peach, yellowgreen } from '@/utils/vuetify'
import { mdiCalendarRange, mdiPulse, mdiTune } from '@mdi/js'
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

const { t } = useI18n({ useScope: 'global' })

const route = useRoute()
const router = useRouter()
const { clickTableRow, closeDetail, item, query, search, searches, changeSearches, updatePage } =
  useDashboard<ResidualStressModel>(route, router, ResidualStressField)

const countsStore = useCountsStore()
onMounted(() => countsStore.fetch())

const parallelFields: ParallelField<ResidualStressField>[] = [
  { id: ResidualStressField.Steel, name: 'Steel Grade' },
  { id: ResidualStressField.HOverB, name: 'h/bf' },
  { id: ResidualStressField.Tf, name: 'tf [mm]' },
  { id: ResidualStressField.A, name: 'A [mm²]' },
  { id: ResidualStressField.Sigma0F, name: 'σ0,f [MPa]' },
  { id: ResidualStressField.Sigma0W, name: 'σ0,w [MPa] ' }
]
const profileFields: DoubleFields<ResidualStressField> = [
  ResidualStressField.Date,
  ResidualStressField.ProfileType
]

const railGroups = computed<FilterRailGroup[]>(() => [
  {
    key: ResidualStressField.Date,
    label: t('dashboards.residual.rail_measurement_date'),
    icon: mdiCalendarRange,
    type: 'range',
    min: 1950,
    max: 2026
  },
  {
    key: ResidualStressField.Tf,
    label: t('dashboards.residual.rail_flange_thickness'),
    icon: mdiTune,
    type: 'range'
  },
  {
    key: ResidualStressField.HOverB,
    label: t('dashboards.residual.rail_aspect_ratio'),
    icon: mdiTune,
    type: 'range'
  },
  {
    key: ResidualStressField.Sigma0F,
    label: t('dashboards.residual.rail_flange_residual_stress'),
    icon: mdiPulse,
    type: 'range'
  },
  {
    key: ResidualStressField.Sigma0W,
    label: t('dashboards.residual.rail_web_residual_stress'),
    icon: mdiPulse,
    type: 'range'
  }
])
</script>

<template>
  <dashboard-shell
    v-model:search="search"
    :eyebrow="$t('dashboards.common.eyebrow_materials')"
    :title="$t('dashboards.residual.title')"
    :count="countsStore.counts.residuals"
    count-label="specimens"
    :description="$t('dashboards.residual.description')"
    i18n-prefix="residual."
    :rail-groups="railGroups"
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
          quiet
          :title="$t('dashboards.residual.chart_steel_grade')"
          :hint="$t('dashboards.common.hint_click_to_filter')"
        >
          <residual-single-chart
            :color="cobalt"
            :field="ResidualStressField.Steel"
            :query="query"
            :show-reset="false"
            flat
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell
          :title="$t('dashboards.residual.chart_specimens_per_year_profile')"
          :hint="$t('dashboards.common.hint_click_legend_to_filter')"
        >
          <residual-double-chart
            :color="peach"
            :fields="profileFields"
            :query="query"
            type="line"
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell
          :title="$t('dashboards.residual.chart_section_height_profile')"
          :hint="$t('dashboards.common.hint_stacked_histogram')"
        >
          <residual-double-chart
            :color="yellowgreen"
            :fields="[ResidualStressField.H, ResidualStressField.ProfileType]"
            :query="query"
            type="bar"
            @change:searches="changeSearches"
          />
        </chart-cell>
      </div>

      <div class="charts-strip charts-strip-1col">
        <chart-cell>
          <residual-parallel-chart
            :color="cobalt"
            :fields="parallelFields"
            :query="query"
            @change:searches="changeSearches"
          />
        </chart-cell>
      </div>
    </template>

    <template #detail>
      <residual-detail v-if="item" :residual="item" @close="closeDetail" />
    </template>
  </dashboard-shell>
</template>
