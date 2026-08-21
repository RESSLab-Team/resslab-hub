<script setup lang="ts">
import { DuctileFractureField, type DuctileFractureModel } from '@/backend'
import ChartCell from '@/components/commons/ChartCell.vue'
import DashboardShell from '@/components/commons/DashboardShell.vue'
import DuctileFractureDoubleChart from '@/components/ductile-fracture/charts/DuctileFractureDoubleChart.vue'
import DuctileFractureParallelChart from '@/components/ductile-fracture/charts/DuctileFractureParallelChart.vue'
import DuctileFractureSingleChart from '@/components/ductile-fracture/charts/DuctileFractureSingleChart.vue'
import DuctileFractureDetail from '@/components/ductile-fracture/DuctileFractureDetail.vue'
import DuctileFractureTable from '@/components/ductile-fracture/DuctileFractureTable.vue'
import type { DoubleFields, ParallelField } from '@/composables/chart'
import { DUCTILE_FRACTURE_KEY, fetchDuctileFractures } from '@/components/ductile-fracture/data'
import { useDashboard } from '@/composables/dashboard'
import { useAutoFilters } from '@/composables/useAutoFilters'
import { useCountsStore } from '@/stores/counts'
import { apricot, mauve, mint, periwinkle, sky } from '@/utils/vuetify'
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

const parallelFilterFields: string[] = [
  DuctileFractureField.Id,
  ...parallelFields.flatMap((f) =>
    typeof f.id === 'string'
      ? [f.id]
      : 'dividend' in f.id
      ? [`${f.id.dividend}/${f.id.divisor}`]
      : []
  )
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

// Filters are derived from the data dictionary + the loaded dataset, so a new
// column becomes filterable without touching this file; `pinned` only keeps the
// long-standing filters at the top of the rail.
const { filters, loading: filtersLoading } = useAutoFilters({
  database: 'ductile-fracture',
  datasetKey: DUCTILE_FRACTURE_KEY,
  fetchAll: fetchDuctileFractures,
  i18nPrefix: 'ductile_fracture.',
  pinned: [
    DuctileFractureField.Date,
    DuctileFractureField.FYn,
    DuctileFractureField.TriaxAvgTillFr,
    DuctileFractureField.LodeAvgTillFr,
    DuctileFractureField.HasSem
  ]
})
</script>

<template>
  <dashboard-shell
    v-model:search="search"
    :eyebrow="$t('dashboards.common.eyebrow_materials')"
    :title="$t('dashboards.ductile_fracture.title')"
    :count="countsStore.counts['ductile-fracture']"
    :description="$t('dashboards.ductile_fracture.description')"
    database-id="ductile-fracture"
    i18n-prefix="ductile_fracture."
    :filters="filters"
    :filters-loading="filtersLoading"
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
          :title="$t('dashboards.ductile_fracture.chart_tests_per_year')"
          :hint="$t('dashboards.common.hint_click_legend_to_filter')"
          :field="dateSpecimenFields"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <ductile-fracture-double-chart
            :color="apricot"
            :fields="dateSpecimenFields"
            type="bar"
            @change:searches="changeSearches"
          />
        </chart-cell>
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
            :show-reset="false"
            flat
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
            type="bar"
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
          <ductile-fracture-parallel-chart
            :fields="parallelFields"
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
