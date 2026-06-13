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
import type { DoubleFields, ParallelField } from '@/composables/chart'
import { useDashboard } from '@/composables/dashboard'
import { useCountsStore } from '@/stores/counts'
import { apricot, mauve, sky } from '@/utils/vuetify'
import { mdiCalendarRange, mdiPulse, mdiTune } from '@mdi/js'
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const { clickTableRow, closeDetail, item, query, search, searches, changeSearches, updatePage } =
  useDashboard<BraceModel>(route, router, BraceField)

const countsStore = useCountsStore()
onMounted(() => countsStore.fetch())

const parallelFields: ParallelField<BraceField>[] = [
  { id: BraceField.KlR },
  {
    id: {
      dividend: BraceField.DBr,
      divisor: BraceField.TBr
    }
  },
  { id: BraceField.CrossSectionShape },
  { id: BraceField.BoundaryCondition }
]
const boundaryConditionFields: DoubleFields<BraceField> = [
  BraceField.Date,
  BraceField.BoundaryCondition
]

const railGroups: FilterRailGroup[] = [
  {
    key: BraceField.Date,
    label: 'Test date',
    icon: mdiCalendarRange,
    type: 'range',
    min: 1970,
    max: 2026
  },
  {
    key: BraceField.KlR,
    label: 'Slenderness kL/r',
    icon: mdiPulse,
    type: 'range'
  },
  {
    key: BraceField.DBr,
    label: 'Section depth d [mm]',
    icon: mdiTune,
    type: 'range'
  }
]
</script>

<template>
  <dashboard-shell
    v-model:search="search"
    eyebrow="Components · Database"
    title="Braces"
    :count="countsStore.counts.braces"
    description="Steel brace tests under reversed cyclic axial loading, covering a range of
      cross-section shapes, slenderness ratios and boundary conditions. Filter through the
      filters panel, the table column filters or the charts below; click a row for the full
      specimen detail and digitized test data."
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
        <chart-cell quiet title="Loading protocol" hint="Click to filter">
          <brace-single-chart
            :color="apricot"
            :field="BraceField.LoadingProtocol"
            :query="query"
            :show-reset="false"
            flat
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell title="Tests per year × boundary condition" hint="Click legend to filter">
          <brace-double-chart
            :color="sky"
            :fields="boundaryConditionFields"
            :query="query"
            type="line"
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell quiet title="Steel grade" hint="Click to filter">
          <brace-single-chart
            :color="mauve"
            :field="BraceField.Steel"
            :query="query"
            :show-reset="false"
            flat
            @change:searches="changeSearches"
          />
        </chart-cell>
      </div>

      <div class="charts-strip charts-strip-1col">
        <chart-cell>
          <brace-parallel-chart
            :color="apricot"
            :fields="parallelFields"
            :query="query"
            @change:searches="changeSearches"
          />
        </chart-cell>
      </div>
    </template>

    <template #detail>
      <brace-detail v-if="item" :brace="item" @close="closeDetail" />
    </template>
  </dashboard-shell>
</template>
