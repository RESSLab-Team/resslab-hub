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
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

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

const railGroups: FilterRailGroup[] = [
  {
    key: MaterialField.Year,
    label: 'Test year',
    icon: mdiCalendarRange,
    type: 'range',
    min: 1970,
    max: 2026
  },
  {
    key: MaterialField.YieldStressMpa,
    label: 'Yield stress [MPa]',
    icon: mdiPulse,
    type: 'range'
  },
  {
    key: MaterialField.FractureStrain,
    label: 'Fracture strain',
    icon: mdiTune,
    type: 'range'
  },
  {
    key: MaterialField.Thickness,
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
    title="Cyclic Coupons"
    :count="countsStore.counts.cyclic"
    count-label="coupons"
    description="Cyclic coupon tests on structural steels with calibrated Updated Voce-Chaboche
      material model parameters. Filter through the filters panel, the table column filters or
      the charts below; click a row for the full coupon detail and digitized stress-strain data."
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
        <chart-cell quiet title="Steel type" hint="Click to filter">
          <material-single-chart
            :color="plum"
            :field="MaterialField.Type"
            :query="query"
            :show-reset="false"
            flat
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell title="Coupons per year × profile type" hint="Click legend to filter">
          <material-double-chart
            :color="periwinkle"
            :fields="profileFields"
            :query="query"
            type="line"
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell title="Thickness × profile type" hint="Stacked histogram · click bar or legend">
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
