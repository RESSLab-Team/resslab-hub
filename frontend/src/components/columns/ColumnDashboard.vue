<script setup lang="ts">
import { ColumnField, type ColumnModel } from '@/backend'
import ColumnDoubleChart from '@/components/columns/charts/ColumnDoubleChart.vue'
import ColumnParallelChart from '@/components/columns/charts/ColumnParallelChart.vue'
import ColumnSingleChart from '@/components/columns/charts/ColumnSingleChart.vue'
import ColumnDetail from '@/components/columns/ColumnDetail.vue'
import ColumnTable from '@/components/columns/ColumnTable.vue'
import InfoTooltip from '@/components/commons/InfoTooltip.vue'
import SteelTypeCardTitle from '@/components/commons/SteelTypeCardTitle.vue'
import type { DoubleFields, ParallelField } from '@/composables/chart'
import { useDashboard } from '@/composables/dashboard'
import { useRoute } from 'vue-router'
import colors from 'vuetify/lib/util/colors'

const route = useRoute()
const { clickTableRow, closeDetail, item, query, search, searches, changeSearches, updatePage } =
  useDashboard<ColumnModel>(route, ColumnField)

const parallelFields: ParallelField<ColumnField>[] = [
  { id: ColumnField.Th80 },
  { id: ColumnField.HOverTCw },
  { id: ColumnField.BFOverTCf },
  { id: ColumnField.LBOverRYc },
  { id: ColumnField.PGOverPYm }
]
const boundaryConditionFields: DoubleFields<ColumnField> = [
  ColumnField.Date,
  ColumnField.BoundaryCondition
]
const columnDepthFields: DoubleFields<ColumnField> = [
  ColumnField.DC,
  {
    id: ColumnField.BuiltUp,
    mapping: new Map([
      ['False', 'Hot Rolled'],
      ['True', 'Built Up']
    ])
  }
]
const steelField = ColumnField.SteelC
</script>

<template>
  <v-row>
    <v-col md="6">
      <v-row>
        <v-col cols="12">
          <column-table
            v-model:search="search"
            v-model:searches="searches"
            :query="query"
            @click:row="clickTableRow"
            @update:page="updatePage"
          />
        </v-col>
      </v-row>
      <v-row v-if="!item">
        <v-col cols="12">
          <column-parallel-chart
            :color="colors.orange"
            :fields="parallelFields"
            :query="query"
            @change:searches="changeSearches"
          />
        </v-col>
      </v-row>
    </v-col>
    <v-col md="6">
      <v-row v-if="item">
        <v-col cols="12">
          <column-detail :column="item" @close="closeDetail" />
        </v-col>
      </v-row>
      <v-row v-else>
        <v-col cols="12" md="6">
          <v-card>
            <v-card-title>Boundary Condition</v-card-title>
            <v-card-text>
              <column-double-chart
                :fields="boundaryConditionFields"
                :query="query"
                type="line"
                @change:searches="changeSearches"
              />
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" md="6">
          <v-card>
            <v-card-title>
              Column Depth [mm]
              <info-tooltip>
                <p>This histogram displays the distribution of column depths in the Database.</p>
                How to use?
                <ul>
                  <li>
                    Filter database for specific column depths, by clicking on a bar or using the
                    slider below
                  </li>
                  <li>
                    Filter database for built-up or hot-rolled cross sections by clicking on the
                    appropriate legend
                  </li>
                </ul>
              </info-tooltip>
            </v-card-title>
            <v-card-text>
              <column-double-chart
                :color="colors.green"
                :fields="columnDepthFields"
                :query="query"
                @change:searches="changeSearches"
              />
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12">
          <column-single-chart
            :color="colors.deepPurple"
            :field="steelField"
            :query="query"
            @change:searches="changeSearches"
          >
            <template #title>
              <steel-type-card-title />
            </template>
          </column-single-chart>
        </v-col>
      </v-row>
    </v-col>
  </v-row>
</template>
