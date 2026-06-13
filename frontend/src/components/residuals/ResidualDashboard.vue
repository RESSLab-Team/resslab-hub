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
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

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

const railGroups: FilterRailGroup[] = [
  {
    key: ResidualStressField.Date,
    label: 'Measurement date',
    icon: mdiCalendarRange,
    type: 'range',
    min: 1950,
    max: 2026
  },
  {
    key: ResidualStressField.Tf,
    label: 'Flange thickness tf [mm]',
    icon: mdiTune,
    type: 'range'
  },
  {
    key: ResidualStressField.HOverB,
    label: 'Aspect ratio h/bf',
    icon: mdiTune,
    type: 'range'
  },
  {
    key: ResidualStressField.Sigma0F,
    label: 'Flange residual stress σ0,f [MPa]',
    icon: mdiPulse,
    type: 'range'
  },
  {
    key: ResidualStressField.Sigma0W,
    label: 'Web residual stress σ0,w [MPa]',
    icon: mdiPulse,
    type: 'range'
  }
]
</script>

<template>
  <dashboard-shell
    v-model:search="search"
    eyebrow="Materials · Database"
    title="Residual Stresses"
    :count="countsStore.counts.residuals"
    count-label="specimens"
    description="Residual stress measurements on hot-rolled and welded steel profiles, with
      flange and web distribution data. Filter through the filters panel, the table column
      filters or the charts below; click a row for the full specimen detail and measured
      distributions."
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
        <chart-cell quiet title="Steel grade" hint="Click to filter">
          <residual-single-chart
            :color="cobalt"
            :field="ResidualStressField.Steel"
            :query="query"
            :show-reset="false"
            flat
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell title="Specimens per year × profile type" hint="Click legend to filter">
          <residual-double-chart
            :color="peach"
            :fields="profileFields"
            :query="query"
            type="line"
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell
          title="Section height × profile type"
          hint="Stacked histogram · click bar or legend"
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
