<script setup lang="ts">
import { MaterialField, type MaterialModel } from '@/backend'
import ChartCell from '@/components/commons/ChartCell.vue'
import DashboardShell from '@/components/commons/DashboardShell.vue'
import MaterialDoubleChart from '@/components/materials/charts/MaterialDoubleChart.vue'
import MaterialParallelChart from '@/components/materials/charts/MaterialParallelChart.vue'
import MaterialSingleChart from '@/components/materials/charts/MaterialSingleChart.vue'
import MaterialDetail from '@/components/materials/MaterialDetail.vue'
import MaterialTable from '@/components/materials/MaterialTable.vue'
import { MATERIAL_KEY, PARALLEL_FIELDS, fetchMaterials } from '@/components/materials/data'
import type { DoubleFields } from '@/composables/chart'
import { useDashboard } from '@/composables/dashboard'
import { useAutoFilters } from '@/composables/useAutoFilters'
import { useCountsStore } from '@/stores/counts'
import { apricot, periwinkle, plum } from '@/utils/vuetify'
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const { clickTableRow, closeDetail, item, query, search, searches, changeSearches, updatePage } =
  useDashboard<MaterialModel>(route, router, MaterialField)

const countsStore = useCountsStore()
onMounted(() => countsStore.fetch())

const parallelFields = PARALLEL_FIELDS

const parallelFilterFields: string[] = [
  MaterialField.Id,
  ...parallelFields.flatMap((f) =>
    typeof f.id === 'string'
      ? [f.id]
      : 'dividend' in f.id
      ? [`${f.id.dividend}/${f.id.divisor}`]
      : []
  )
]
const profileFields: DoubleFields<MaterialField> = [MaterialField.Year, MaterialField.ProfileType]
const profileThicknessFields: DoubleFields<MaterialField> = [
  MaterialField.Thickness,
  MaterialField.ProfileType
]

// Filters are derived from the data dictionary + the loaded dataset, so a new
// column becomes filterable without touching this file; `pinned` only keeps the
// long-standing filters at the top of the rail.
const { filters, loading: filtersLoading } = useAutoFilters({
  database: 'cyclic',
  datasetKey: MATERIAL_KEY,
  fetchAll: fetchMaterials,
  i18nPrefix: 'material.',
  pinned: [
    MaterialField.Year,
    MaterialField.YieldStressMpa,
    MaterialField.FractureStrain,
    MaterialField.Thickness
  ]
})
</script>

<template>
  <dashboard-shell
    v-model:search="search"
    :eyebrow="$t('dashboards.common.eyebrow_materials')"
    :title="$t('dashboards.material.title')"
    :count="countsStore.counts.cyclic"
    count-label="coupons"
    :description="$t('dashboards.material.description')"
    database-id="cyclic"
    i18n-prefix="material."
    :filters="filters"
    :filters-loading="filtersLoading"
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
        <chart-cell
          :title="$t('dashboards.material.chart_coupons_per_year_profile')"
          :hint="$t('dashboards.common.hint_click_legend_to_filter')"
          :field="profileFields"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <material-double-chart
            :color="periwinkle"
            :fields="profileFields"
            type="line"
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell
          :title="$t('dashboards.material.chart_thickness_profile')"
          :hint="$t('dashboards.common.hint_stacked_histogram')"
          :field="profileThicknessFields"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <material-double-chart
            :color="apricot"
            :fields="profileThicknessFields"
            type="bar"
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell
          quiet
          :title="$t('dashboards.material.chart_steel_type')"
          :hint="$t('dashboards.common.hint_click_to_filter')"
          :field="MaterialField.Type"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <material-single-chart
            :color="plum"
            :field="MaterialField.Type"
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
          <material-parallel-chart :fields="parallelFields" @change:searches="changeSearches" />
        </chart-cell>
      </div>
    </template>

    <template #detail>
      <material-detail v-if="item" :material="item" @close="closeDetail" />
    </template>
  </dashboard-shell>
</template>
