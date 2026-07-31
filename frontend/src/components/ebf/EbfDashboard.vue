<script setup lang="ts">
import { EccentricBracedFrameField, type EccentricBracedFrameModel } from '@/backend'
import ChartCell from '@/components/commons/ChartCell.vue'
import DashboardShell from '@/components/commons/DashboardShell.vue'
import type { FilterRailGroup } from '@/components/commons/FilterRail.vue'
import EbfDoubleChart from '@/components/ebf/charts/EbfDoubleChart.vue'
import EbfParallelChart from '@/components/ebf/charts/EbfParallelChart.vue'
import EbfSingleChart from '@/components/ebf/charts/EbfSingleChart.vue'
import EbfDetail from '@/components/ebf/EbfDetail.vue'
import EbfTable from '@/components/ebf/EbfTable.vue'
import type { DoubleFields, ParallelField } from '@/composables/chart'
import { useDashboard } from '@/composables/dashboard'
import { useCountsStore } from '@/stores/counts'
import { sectionTypeMapping } from '@/utils/ebf'
import { cobalt, mauve, mint, peach, sky } from '@/utils/vuetify'
import { mdiCalendarRange, mdiPulse, mdiTagOutline, mdiTune } from '@mdi/js'
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

const { t } = useI18n({ useScope: 'global' })

const route = useRoute()
const router = useRouter()
const { clickTableRow, closeDetail, item, query, search, searches, changeSearches, updatePage } =
  useDashboard<EccentricBracedFrameModel>(route, router, EccentricBracedFrameField)

const countsStore = useCountsStore()
onMounted(() => countsStore.fetch())

const parallelFields: ParallelField<EccentricBracedFrameField>[] = [
  { id: EccentricBracedFrameField.E, name: 'e [mm]' },
  { id: EccentricBracedFrameField.LinkLoc, name: 'Location' },
  { id: EccentricBracedFrameField.SecType, name: 'Type' },
  { id: EccentricBracedFrameField.SgFlgLink, name: 'Material' },
  { id: EccentricBracedFrameField.OvAisc, name: 'Ω' },
  {
    id: EccentricBracedFrameField.ClassAisc,
    name: 'Link Classification',
    sortValues: ['long', 'intermediate', 'short']
  }
]

const parallelFilterFields: string[] = [
  EccentricBracedFrameField.Id,
  ...parallelFields.flatMap((f) =>
    typeof f.id === 'string'
      ? [f.id]
      : 'dividend' in f.id
      ? [`${f.id.dividend}/${f.id.divisor}`]
      : []
  )
]
const yearSectionFields: DoubleFields<EccentricBracedFrameField> = [
  EccentricBracedFrameField.Year,
  {
    id: EccentricBracedFrameField.SecType,
    mapping: sectionTypeMapping
  }
]
const yearLinkFields: DoubleFields<EccentricBracedFrameField> = [
  EccentricBracedFrameField.Year,
  {
    id: EccentricBracedFrameField.ClassAisc,
    mapping: sectionTypeMapping
  }
]

const railGroups = computed<FilterRailGroup[]>(() => [
  {
    key: EccentricBracedFrameField.Year,
    label: t('dashboards.ebf.rail_test_year'),
    icon: mdiCalendarRange,
    type: 'range',
    min: 1970,
    max: 2026
  },
  {
    key: EccentricBracedFrameField.E,
    label: t('dashboards.ebf.rail_link_length'),
    icon: mdiTune,
    type: 'range'
  },
  {
    key: EccentricBracedFrameField.ClassAisc,
    label: t('dashboards.ebf.rail_link_classification'),
    icon: mdiTagOutline,
    type: 'chips',
    options: [
      { label: 'Short', value: 'short' },
      { label: 'Intermediate', value: 'intermediate' },
      { label: 'Long', value: 'long' }
    ]
  },
  {
    key: EccentricBracedFrameField.OvAisc,
    label: t('dashboards.ebf.rail_overstrength'),
    icon: mdiPulse,
    type: 'range'
  }
])
</script>

<template>
  <dashboard-shell
    v-model:search="search"
    :eyebrow="$t('dashboards.common.eyebrow_components')"
    :title="$t('dashboards.ebf.title')"
    :count="countsStore.counts.ebf"
    :description="$t('dashboards.ebf.description')"
    database-id="ebf"
    i18n-prefix="ebf."
    :rail-groups="railGroups"
    :searches="searches"
    :detail-open="!!item"
    @change:searches="changeSearches"
    @close:detail="closeDetail"
  >
    <template #table>
      <ebf-table
        v-model:search="search"
        v-model:searches="searches"
        :query="query"
        @click:row="clickTableRow"
        @update:page="updatePage"
      />
    </template>

    <template #charts>
      <div class="charts-strip charts-strip-2cols">
        <chart-cell
          :title="$t('dashboards.ebf.chart_tests_per_year_section')"
          :hint="$t('dashboards.common.hint_click_legend_to_filter')"
          :field="yearSectionFields"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <ebf-double-chart
            :color="peach"
            :fields="yearSectionFields"
            type="line"
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell
          :title="$t('dashboards.ebf.chart_tests_per_year_classification')"
          :hint="$t('dashboards.common.hint_click_legend_to_filter')"
          :field="yearLinkFields"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <ebf-double-chart
            :color="mauve"
            :fields="yearLinkFields"
            type="line"
            @change:searches="changeSearches"
          />
        </chart-cell>
      </div>

      <div class="charts-strip">
        <chart-cell
          quiet
          :title="$t('dashboards.ebf.chart_loading_protocol')"
          :hint="$t('dashboards.common.hint_click_to_filter')"
          :field="EccentricBracedFrameField.LPTyp"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <ebf-single-chart
            :color="cobalt"
            :field="EccentricBracedFrameField.LPTyp"
            :show-reset="false"
            flat
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell
          quiet
          :title="$t('dashboards.ebf.chart_test_configuration')"
          :hint="$t('dashboards.common.hint_click_to_filter')"
          :field="EccentricBracedFrameField.LConfi"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <ebf-single-chart
            :color="mint"
            :field="EccentricBracedFrameField.LConfi"
            :show-reset="false"
            flat
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell
          quiet
          :title="$t('dashboards.ebf.chart_steel_grade')"
          :hint="$t('dashboards.common.hint_click_to_filter')"
          :field="EccentricBracedFrameField.SgFlgLink"
          :searches="searches"
          @change:searches="changeSearches"
        >
          <ebf-single-chart
            :color="sky"
            :field="EccentricBracedFrameField.SgFlgLink"
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
          <ebf-parallel-chart :fields="parallelFields" @change:searches="changeSearches" />
        </chart-cell>
      </div>
    </template>

    <template #detail>
      <ebf-detail v-if="item" :eccentric-braced-frame="item" @close="closeDetail" />
    </template>
  </dashboard-shell>
</template>
