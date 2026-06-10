<script setup lang="ts">
import { ConnectionField, type ConnectionModel } from '@/backend'
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
import { mdiClose } from '@mdi/js'
import { computed, onMounted } from 'vue'
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
  <div class="dash">
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
      </div>
      <p class="dash-desc">
        Beam-to-column moment connection tests under reversed cyclic and monotonic loading,
        categorized per AISC-358-16. Filter through the charts below or the table column filters;
        click a row for the full specimen detail and digitized test data.
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

    <!-- Detail drawer -->
    <div class="drawer-scrim" :class="{ open: !!item }" @click="closeDetail" />
    <aside class="drawer" :class="{ open: !!item }">
      <connection-detail v-if="item" :connection="item" @close="closeDetail" />
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
