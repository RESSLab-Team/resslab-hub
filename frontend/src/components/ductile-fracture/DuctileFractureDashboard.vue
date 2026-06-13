<script setup lang="ts">
import { DuctileFractureField, type DuctileFractureModel } from '@/backend'
import ChartCell from '@/components/commons/ChartCell.vue'
import DashboardShell from '@/components/commons/DashboardShell.vue'
import type { FilterRailGroup } from '@/components/commons/FilterRail.vue'
import DuctileFractureDoubleChart from '@/components/ductile-fracture/charts/DuctileFractureDoubleChart.vue'
import DuctileFractureParallelChart from '@/components/ductile-fracture/charts/DuctileFractureParallelChart.vue'
import DuctileFractureSingleChart from '@/components/ductile-fracture/charts/DuctileFractureSingleChart.vue'
import DuctileFractureDetail from '@/components/ductile-fracture/DuctileFractureDetail.vue'
import DuctileFractureTable from '@/components/ductile-fracture/DuctileFractureTable.vue'
import type { DoubleFields, ParallelField } from '@/composables/chart'
import { useDashboard } from '@/composables/dashboard'
import { useCountsStore } from '@/stores/counts'
import { apricot, mauve, mint, periwinkle, sky } from '@/utils/vuetify'
import { mdiCalendarRange, mdiImageOutline, mdiPulse, mdiTune } from '@mdi/js'
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const { clickTableRow, closeDetail, item, query, search, searches, changeSearches, updatePage } =
  useDashboard<DuctileFractureModel>(route, router, DuctileFractureField)

const countsStore = useCountsStore()
onMounted(() => countsStore.fetch())

const parallelFields: ParallelField<DuctileFractureField>[] = [
  { id: DuctileFractureField.SteelType },
  { id: DuctileFractureField.FYn },
  { id: DuctileFractureField.SpecimenType },
  { id: DuctileFractureField.NomNotchRadius },
  { id: DuctileFractureField.LodeAvgTillFr },
  { id: DuctileFractureField.TriaxAvgTillFr },
  { id: DuctileFractureField.PeeqAtFr },
  { id: DuctileFractureField.LocationCoupon },
  {
    id: {
      key: 'cev',
      fields: [
        DuctileFractureField.ChemicalCompositionC,
        DuctileFractureField.ChemicalCompositionMn,
        DuctileFractureField.ChemicalCompositionSi,
        DuctileFractureField.ChemicalCompositionCr,
        DuctileFractureField.ChemicalCompositionMo,
        DuctileFractureField.ChemicalCompositionV,
        DuctileFractureField.ChemicalCompositionNi,
        DuctileFractureField.ChemicalCompositionCu
      ],
      compute: ([c, mn, si, cr, mo, v, ni, cu]) =>
        [c, mn, si, cr, mo, v, ni, cu].some((x) => x == null)
          ? null
          : c! + mn! / 6 + si! / 6 + (cr! + mo! + v!) / 5 + (ni! + cu!) / 15
    }
  }
]
const dateSpecimenFields: DoubleFields<DuctileFractureField> = [
  DuctileFractureField.Date,
  DuctileFractureField.SpecimenType
]
const triaxSpecimenFields: DoubleFields<DuctileFractureField> = [
  DuctileFractureField.TriaxAvgTillFr,
  DuctileFractureField.SpecimenType
]
const lodeSpecimenFields: DoubleFields<DuctileFractureField> = [
  DuctileFractureField.LodeAvgTillFr,
  DuctileFractureField.SpecimenType
]

const railGroups: FilterRailGroup[] = [
  {
    key: DuctileFractureField.Date,
    label: 'Test date',
    icon: mdiCalendarRange,
    type: 'range',
    min: 1990,
    max: 2026
  },
  {
    key: DuctileFractureField.FYn,
    label: 'Nominal yield stress [MPa]',
    icon: mdiPulse,
    type: 'range'
  },
  {
    key: DuctileFractureField.TriaxAvgTillFr,
    label: 'Avg triaxiality to fracture',
    icon: mdiTune,
    type: 'range'
  },
  {
    key: DuctileFractureField.LodeAvgTillFr,
    label: 'Avg Lode angle to fracture',
    icon: mdiTune,
    type: 'range'
  },
  {
    key: DuctileFractureField.HasSem,
    label: 'SEM imagery',
    icon: mdiImageOutline,
    type: 'chips',
    options: [
      { label: 'With SEM', value: 'true' },
      { label: 'Without', value: 'false' }
    ]
  }
]
</script>

<template>
  <dashboard-shell
    v-model:search="search"
    eyebrow="Materials · Database"
    title="Ductile Fracture"
    :count="countsStore.counts['ductile-fracture']"
    description="Ductile fracture tests on notched steel coupons with simulated stress-state
      histories (triaxiality, Lode angle) and calibrated fracture model parameters. Filter
      through the filters panel, the table column filters or the charts below; click a row for
      the full specimen detail, test data and SEM imagery."
    i18n-prefix="ductile_fracture."
    :rail-groups="railGroups"
    :searches="searches"
    :detail-open="!!item"
    @change:searches="changeSearches"
    @close:detail="closeDetail"
  >
    <template #table>
      <ductile-fracture-table
        v-model:search="search"
        v-model:searches="searches"
        :query="query"
        @click:row="clickTableRow"
        @update:page="updatePage"
      />
    </template>

    <template #charts>
      <div class="charts-strip">
        <chart-cell quiet title="Specimen type" hint="Click to filter">
          <ductile-fracture-single-chart
            :color="mauve"
            :field="DuctileFractureField.SpecimenType"
            :query="query"
            :show-reset="false"
            flat
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell title="Tests per year × specimen type" hint="Click legend to filter">
          <ductile-fracture-double-chart
            :color="apricot"
            :fields="dateSpecimenFields"
            :query="query"
            type="bar"
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell quiet title="Steel type" hint="Click to filter">
          <ductile-fracture-single-chart
            :color="periwinkle"
            :field="DuctileFractureField.SteelType"
            :query="query"
            :show-reset="false"
            flat
            @change:searches="changeSearches"
          />
        </chart-cell>
      </div>

      <div class="charts-strip charts-strip-2cols">
        <chart-cell
          title="Triaxiality × specimen type"
          hint="Stacked histogram · click bar or legend"
        >
          <ductile-fracture-double-chart
            :color="mint"
            :fields="triaxSpecimenFields"
            :query="query"
            type="bar"
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell
          title="Lode angle × specimen type"
          hint="Stacked histogram · click bar or legend"
        >
          <ductile-fracture-double-chart
            :color="sky"
            :fields="lodeSpecimenFields"
            :query="query"
            type="bar"
            @change:searches="changeSearches"
          />
        </chart-cell>
      </div>

      <div class="charts-strip charts-strip-1col">
        <chart-cell>
          <ductile-fracture-parallel-chart
            :color="mauve"
            :fields="parallelFields"
            :query="query"
            @change:searches="changeSearches"
          />
        </chart-cell>
      </div>
    </template>

    <template #detail>
      <ductile-fracture-detail v-if="item" :ductile-fracture="item" @close="closeDetail" />
    </template>
  </dashboard-shell>
</template>
