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
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

const { t } = useI18n({ useScope: 'global' })

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

const railGroups = computed<FilterRailGroup[]>(() => [
  {
    key: DuctileFractureField.Date,
    label: t('dashboards.ductile_fracture.rail_test_date'),
    icon: mdiCalendarRange,
    type: 'range',
    min: 1990,
    max: 2026
  },
  {
    key: DuctileFractureField.FYn,
    label: t('dashboards.ductile_fracture.rail_nominal_yield_stress'),
    icon: mdiPulse,
    type: 'range'
  },
  {
    key: DuctileFractureField.TriaxAvgTillFr,
    label: t('dashboards.ductile_fracture.rail_avg_triaxiality'),
    icon: mdiTune,
    type: 'range'
  },
  {
    key: DuctileFractureField.LodeAvgTillFr,
    label: t('dashboards.ductile_fracture.rail_avg_lode_angle'),
    icon: mdiTune,
    type: 'range'
  },
  {
    key: DuctileFractureField.HasSem,
    label: t('dashboards.ductile_fracture.rail_sem_imagery'),
    icon: mdiImageOutline,
    type: 'chips',
    options: [
      { label: t('dashboards.ductile_fracture.rail_sem_with'), value: 'true' },
      { label: t('dashboards.ductile_fracture.rail_sem_without'), value: 'false' }
    ]
  }
])
</script>

<template>
  <dashboard-shell
    v-model:search="search"
    :eyebrow="$t('dashboards.common.eyebrow_materials')"
    :title="$t('dashboards.ductile_fracture.title')"
    :count="countsStore.counts['ductile-fracture']"
    :description="$t('dashboards.ductile_fracture.description')"
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
        <chart-cell
          quiet
          :title="$t('dashboards.ductile_fracture.chart_specimen_type')"
          :hint="$t('dashboards.common.hint_click_to_filter')"
          :field="DuctileFractureField.SpecimenType"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <ductile-fracture-single-chart
            :color="mauve"
            :field="DuctileFractureField.SpecimenType"
            :query="query"
            :show-reset="false"
            flat
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell
          :title="$t('dashboards.ductile_fracture.chart_tests_per_year')"
          :hint="$t('dashboards.common.hint_click_legend_to_filter')"
          :field="dateSpecimenFields"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <ductile-fracture-double-chart
            :color="apricot"
            :fields="dateSpecimenFields"
            :query="query"
            type="bar"
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell
          quiet
          :title="$t('dashboards.ductile_fracture.chart_steel_type')"
          :hint="$t('dashboards.common.hint_click_to_filter')"
          :field="DuctileFractureField.SteelType"
          :searches="searches"
          @change:searches="changeSearches"
        >
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
          :title="$t('dashboards.ductile_fracture.chart_triaxiality')"
          :hint="$t('dashboards.common.hint_stacked_histogram')"
          :field="triaxSpecimenFields"
          :searches="searches"
          @change:searches="changeSearches"
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
          :title="$t('dashboards.ductile_fracture.chart_lode_angle')"
          :hint="$t('dashboards.common.hint_stacked_histogram')"
          :field="lodeSpecimenFields"
          :searches="searches"
          @change:searches="changeSearches"
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
