<script setup lang="ts">
import { ConnectionField, type ConnectionModel } from '@/backend'
import FilterRail, { type FilterRailGroup } from '@/components/commons/FilterRail.vue'
import ConnectionDoubleChart from '@/components/connections/charts/ConnectionDoubleChart.vue'
import ConnectionParallelChart from '@/components/connections/charts/ConnectionParallelChart.vue'
import ConnectionSingleChart from '@/components/connections/charts/ConnectionSingleChart.vue'
import ConnectionDetail from '@/components/connections/ConnectionDetail.vue'
import ConnectionTable from '@/components/connections/ConnectionTable.vue'
import type { DoubleFields, ParallelField } from '@/composables/chart'
import { useDashboard } from '@/composables/dashboard'
import i18n from '@/plugins/i18n'
import { useCountsStore } from '@/stores/counts'
import type { Value } from '@/utils/common'
import { cobalt, peach, periwinkle, plum, sky } from '@/utils/vuetify'
import {
  mdiCalendarRange,
  mdiClose,
  mdiFilterVariant,
  mdiHistory,
  mdiLayersOutline,
  mdiPulse,
  mdiTagOutline,
  mdiTune,
  mdiViewGridOutline
} from '@mdi/js'
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const { clickTableRow, closeDetail, item, query, search, searches, changeSearches, updatePage } =
  useDashboard<ConnectionModel>(route, router, ConnectionField)

const countsStore = useCountsStore()
onMounted(() => countsStore.fetch())

const parallelFields: ParallelField<ConnectionField>[] = [
  {
    id: ConnectionField.DB,
    name: 'Beam Depth\ndb [mm]'
  },
  {
    id: ConnectionField.DC,
    name: 'Column Depth\ndc [mm]'
  },
  {
    id: ConnectionField.TCf,
    name: 'Column flange\nThickness [mm]'
  },
  {
    id: {
      dividend: ConnectionField.DB,
      divisor: ConnectionField.DC
    },
    name: 'db / dc'
  },
  {
    id: ConnectionField.GMaxGY
  },
  {
    id: ConnectionField.RuRnPlN
  },
  {
    id: ConnectionField.ConnectionType,
    name: 'Connection\nType'
  }
]
const beamFields: DoubleFields<ConnectionField> = [
  ConnectionField.DB,
  {
    id: ConnectionField.Slab,
    mapping: new Map([
      ['False', 'Bare'],
      ['True', 'Composite']
    ])
  }
]

/* ---- filter rail (design handoff: right-anchored, collapsible) ---- */
const railGroups: FilterRailGroup[] = [
  {
    key: ConnectionField.ConnectionType,
    label: 'Connection type',
    icon: mdiTagOutline,
    type: 'chips',
    redChips: true,
    options: ['WUF-W', 'RBS', 'WUF-B', 'BFP', 'WFP', 'KBB', 'BEEP']
  },
  {
    key: ConnectionField.Date,
    label: 'Test date',
    icon: mdiCalendarRange,
    type: 'range',
    min: 1970,
    max: 2026
  },
  {
    key: ConnectionField.Northridge,
    label: 'Northridge',
    icon: mdiHistory,
    type: 'chips',
    options: [
      { label: 'Pre-1994', value: 'pre' },
      { label: 'Post-1994', value: 'post' }
    ]
  },
  {
    key: ConnectionField.SpecimenType,
    label: 'Specimen type',
    icon: mdiViewGridOutline,
    type: 'chips',
    options: [
      { label: 'Interior', value: 'interior%' },
      { label: 'Exterior', value: 'exterior%' }
    ]
  },
  {
    key: ConnectionField.Slab,
    label: 'Composite slab',
    icon: mdiLayersOutline,
    type: 'chips',
    options: [
      { label: 'Bare', value: 'false' },
      { label: 'Composite', value: 'true' }
    ]
  },
  {
    key: ConnectionField.DB,
    label: 'Beam depth db [mm]',
    icon: mdiTune,
    type: 'range'
  },
  {
    key: ConnectionField.TCf,
    label: 'Column flange tcf [mm]',
    icon: mdiTune,
    type: 'range'
  },
  {
    key: ConnectionField.GMaxGY,
    label: 'Panel-zone γmax/γy',
    icon: mdiPulse,
    type: 'range'
  }
]

// Auto-collapse the rail on narrower laptops; the user can re-expand it.
const collapseQuery = window.matchMedia('(max-width: 1399px)')
const railCollapsed = ref<boolean>(collapseQuery.matches)
const filtersOverlayOpen = ref<boolean>(false)
function onCollapseQueryChange(event: MediaQueryListEvent): void {
  railCollapsed.value = event.matches
}
onMounted(() => collapseQuery.addEventListener('change', onCollapseQueryChange))
onUnmounted(() => collapseQuery.removeEventListener('change', onCollapseQueryChange))

const railFilterCount = computed<number>(
  () => railGroups.filter((group) => searches.value[group.key] != null).length
)

/* ---- active-filter chips (mirrors the searches driving table + charts) ---- */
function formatChipValue(value: Value): string {
  if (Array.isArray(value)) {
    if (value.length === 2 && value.every((v) => !isNaN(Number(v)))) {
      return `${value[0]} – ${value[1]}`
    }
    return `${value.length} selected`
  }
  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No'
  }
  const text = String(value)
  if (text.includes('<<')) {
    return text.split('<<', 2).join(' – ')
  }
  return text.length > 32 ? `${text.split(',').length} selected` : text
}

const activeChips = computed(() =>
  Object.entries(searches.value).map(([key, value]) => ({
    key,
    label: `${i18n.global.t('connection.' + key)}: ${formatChipValue(value)}`
  }))
)

function clearAll(): void {
  Object.keys(searches.value).forEach((key) => changeSearches(key, undefined))
}
</script>

<template>
  <div
    class="dash dash-with-rail"
    :class="{ 'rail-collapsed': railCollapsed }"
    data-filter-pos="right"
  >
    <filter-rail
      :collapsed="railCollapsed"
      :groups="railGroups"
      position="right"
      :searches="searches"
      @change:searches="changeSearches"
      @update:collapsed="railCollapsed = $event"
    />

    <div class="dash-main">
      <!-- Page header -->
      <div class="dash-head">
        <div class="eyebrow" style="margin-bottom: 6px">Components · Database</div>
        <div class="dash-head-row">
          <h1 class="dash-title">
            Connections
            <span v-if="countsStore.counts.connections != null" class="dash-title-count">
              {{ countsStore.counts.connections.toLocaleString('en-CH') }} tests
            </span>
          </h1>
          <button
            class="btn btn-secondary btn-sm dash-filters-trigger"
            @click="filtersOverlayOpen = true"
          >
            <v-icon :icon="mdiFilterVariant" size="14" />
            Filters
            <span v-if="railFilterCount > 0" class="dash-filters-trigger-badge">
              {{ railFilterCount }}
            </span>
          </button>
        </div>
        <p class="dash-desc">
          Beam-to-column moment connection tests under reversed cyclic and monotonic loading,
          categorized per AISC-358-16. Filter through the rail, the charts below or the table column
          filters; click a row for the full specimen detail and digitized test data.
        </p>
      </div>

      <!-- Active filters -->
      <div v-if="activeChips.length > 0" class="dash-active-filters">
        <strong>Active filters</strong>
        <span v-for="chip in activeChips" :key="chip.key" class="fchip">
          {{ chip.label }}
          <span
            class="fchip-x"
            role="button"
            :aria-label="`Remove filter ${chip.label}`"
            @click="changeSearches(chip.key, undefined)"
          >
            <v-icon :icon="mdiClose" size="10" />
          </span>
        </span>
        <button class="chip-clear" @click="clearAll">
          <v-icon :icon="mdiClose" size="10" />
          Clear all
        </button>
      </div>

      <!-- Charts — row 1: distributions -->
      <div class="charts-strip">
        <div class="chart-cell chart-cell--quiet">
          <div class="chart-head">
            <h5>Connection type</h5>
            <span class="info">Click a tile to filter</span>
          </div>
          <div class="chart-body">
            <connection-single-chart
              :color="peach"
              :field="ConnectionField.ConnectionType"
              :query="query"
              :show-reset="false"
              flat
              @change:searches="changeSearches"
            />
          </div>
        </div>
        <div class="chart-cell">
          <div class="chart-head">
            <h5>Tests per year × type</h5>
            <span class="info">Click legend to filter</span>
          </div>
          <div class="chart-body">
            <connection-double-chart
              :color="periwinkle"
              :fields="[ConnectionField.Date, ConnectionField.ConnectionType]"
              :query="query"
              type="line"
              @change:searches="changeSearches"
            />
          </div>
        </div>
        <div class="chart-cell chart-cell--quiet">
          <div class="chart-head">
            <h5>Beam steel grade</h5>
            <span class="info">Click to filter</span>
          </div>
          <div class="chart-body">
            <connection-single-chart
              :color="cobalt"
              :field="ConnectionField.SteelB"
              :query="query"
              :show-reset="false"
              flat
              @change:searches="changeSearches"
            />
          </div>
        </div>
      </div>

      <!-- Charts — row 2: stacked histograms -->
      <div class="charts-strip charts-strip-2cols">
        <div class="chart-cell">
          <div class="chart-head">
            <h5>Beam depth × slab</h5>
            <span class="info">Stacked histogram · click bar or legend</span>
          </div>
          <div class="chart-body">
            <connection-double-chart
              :color="sky"
              :fields="beamFields"
              :query="query"
              @change:searches="changeSearches"
            />
          </div>
        </div>
        <div class="chart-cell">
          <div class="chart-head">
            <h5>Column depth × doubler plates</h5>
            <span class="info">Stacked histogram · click bar or legend</span>
          </div>
          <div class="chart-body">
            <connection-double-chart
              :color="plum"
              :fields="[ConnectionField.DC, ConnectionField.NDp]"
              :query="query"
              @change:searches="changeSearches"
            />
          </div>
        </div>
      </div>

      <!-- Charts — row 3: parallel coordinates (full width) -->
      <div class="charts-strip charts-strip-1col">
        <div class="chart-cell">
          <connection-parallel-chart
            :color="periwinkle"
            :fields="parallelFields"
            :query="query"
            @change:searches="changeSearches"
          />
        </div>
      </div>

      <!-- Table -->
      <div class="dash-table">
        <connection-table
          v-model:search="search"
          v-model:searches="searches"
          :query="query"
          @click:row="clickTableRow"
          @update:page="updatePage"
        />
      </div>
    </div>

    <!-- Detail drawer -->
    <div class="drawer-scrim" :class="{ open: !!item }" @click="closeDetail" />
    <aside class="drawer" :class="{ open: !!item }">
      <connection-detail v-if="item" :connection="item" @close="closeDetail" />
    </aside>

    <!-- Filters overlay drawer (narrow viewports) -->
    <div
      class="drawer-scrim"
      :class="{ open: filtersOverlayOpen }"
      @click="filtersOverlayOpen = false"
    />
    <aside class="filters-overlay" :class="{ open: filtersOverlayOpen }">
      <filter-rail
        as-overlay
        :groups="railGroups"
        position="right"
        :searches="searches"
        @change:searches="changeSearches"
        @close="filtersOverlayOpen = false"
      />
    </aside>
  </div>
</template>

<style scoped>
/* Single charts carry their own (empty) v-card-title; the strip provides the
   chart head instead. */
.chart-cell--quiet :deep(.v-card-title) {
  display: none;
}
.chart-cell :deep(.v-card) {
  border: 0 !important;
}
</style>
