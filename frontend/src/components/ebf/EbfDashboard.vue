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
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

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

const railGroups: FilterRailGroup[] = [
  {
    key: EccentricBracedFrameField.Year,
    label: 'Test year',
    icon: mdiCalendarRange,
    type: 'range',
    min: 1970,
    max: 2026
  },
  {
    key: EccentricBracedFrameField.E,
    label: 'Link length e [mm]',
    icon: mdiTune,
    type: 'range'
  },
  {
    key: EccentricBracedFrameField.ClassAisc,
    label: 'Link classification (AISC)',
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
    label: 'Overstrength Ω (AISC)',
    icon: mdiPulse,
    type: 'range'
  }
]
</script>

<template>
  <dashboard-shell
    v-model:search="search"
    eyebrow="Components · Database"
    title="EBF Links"
    :count="countsStore.counts.ebf"
    description="Eccentrically braced frame link tests, classified per AISC-341 link length
      categories across isolated, frame and system test configurations. Filter through the
      filters panel, the table column filters or the charts below; click a row for the full
      specimen detail and digitized test data."
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
        <chart-cell title="Tests per year × section type" hint="Click legend to filter">
          <ebf-double-chart
            :color="peach"
            :fields="yearSectionFields"
            :query="query"
            type="line"
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell title="Tests per year × link classification" hint="Click legend to filter">
          <ebf-double-chart
            :color="mauve"
            :fields="yearLinkFields"
            :query="query"
            type="line"
            @change:searches="changeSearches"
          />
        </chart-cell>
      </div>

      <div class="charts-strip">
        <chart-cell quiet title="Loading protocol" hint="Click to filter">
          <ebf-single-chart
            :color="cobalt"
            :field="EccentricBracedFrameField.LPTyp"
            :query="query"
            :show-reset="false"
            flat
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell quiet title="Test configuration" hint="Click to filter">
          <ebf-single-chart
            :color="mint"
            :field="EccentricBracedFrameField.LConfi"
            :query="query"
            :show-reset="false"
            flat
            @change:searches="changeSearches"
          />
        </chart-cell>
        <chart-cell quiet title="Steel grade" hint="Click to filter">
          <ebf-single-chart
            :color="sky"
            :field="EccentricBracedFrameField.SgFlgLink"
            :query="query"
            :show-reset="false"
            flat
            @change:searches="changeSearches"
          />
        </chart-cell>
      </div>

      <div class="charts-strip charts-strip-1col">
        <chart-cell>
          <ebf-parallel-chart
            :color="peach"
            :fields="parallelFields"
            :query="query"
            @change:searches="changeSearches"
          />
        </chart-cell>
      </div>
    </template>

    <template #detail>
      <ebf-detail v-if="item" :eccentric-braced-frame="item" @close="closeDetail" />
    </template>
  </dashboard-shell>
</template>
