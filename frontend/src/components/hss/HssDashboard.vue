<script setup lang="ts">
import { HSSColumnField, type HSSColumnModel } from '@/backend'
import InfoTooltip from '@/components/commons/InfoTooltip.vue'

import HssTable from '@/components/hss/HssTable.vue'
import HssParallelChart from '@/components/hss/charts/HssParallelChart.vue'
import HssDoubleChart from '@/components/hss/charts/HssDoubleChart.vue'
import HssSingleChart from '@/components/hss/charts/HssSingleChart.vue'
import SteelTypeCardTitle from '@/components/commons/SteelTypeCardTitle.vue'
import ResetChartButton from '@/components/commons/ResetChartButton.vue'

import type { DoubleFields, ParallelField } from '@/composables/chart'
import { useDashboard } from '@/composables/dashboard'
import { useRoute } from 'vue-router'
import colors from 'vuetify/lib/util/colors'

const route = useRoute()
const { clickTableRow, closeDetail, item, query, search, searches, changeSearches, updatePage } =
  useDashboard<HSSColumnModel>(route, HSSColumnField)

const parallelFields: ParallelField<HSSColumnField>[] = [
  { id: HSSColumnField.ThetaPPos100fitRad, name: 'Θp [rad]' },
  { id: HSSColumnField.DepthOverT, name: 'D/t' },
  { id: HSSColumnField.AxialLoadRatio, name: 'Pg/Py' },
  { id: HSSColumnField.LoadingAngle, name: 'Load Angle [degrees]' },
  { id: HSSColumnField.TestConfiguration, name: 'Boundary Condition' }
]

const failureModeFields: DoubleFields<HSSColumnField> = [
  HSSColumnField.Date,
  HSSColumnField.FlexuralBuckling
]
const loadingProtocolField = HSSColumnField.LoadingProtocol
const steelField = HSSColumnField.SteelType
</script>

<template>
  <v-row>
    <v-col md="6">
      <v-row>
        <v-col cols="12">
          <hss-table
            v-model:search="search"
            v-model:searches="searches"
            :query="query"
            @click:row="clickTableRow"
            @update:page="updatePage"
          />
        </v-col>
      </v-row>
      <v-row v-if="!item">
        <v-col cols="12"
          ><hss-parallel-chart
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
        <v-col cols="12"> hss detail </v-col>
      </v-row>
      <v-row v-else>
        <v-col cols="12" md="6">
          <v-card>
            <v-card-title class="d-flex justify-space-between">
              Failure Mode
              <reset-chart-button
                :field="failureModeFields"
                :is-filtered="failureModeFields.some(field => query.includes(field as string))"
                @change:searches="changeSearches"
            /></v-card-title>
            <v-card-text>
              <hss-double-chart
                :fields="failureModeFields"
                :query="query"
                type="line"
                @change:searches="changeSearches"
              />
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" md="6">
          <hss-single-chart
            :show-reset="true"
            :color="colors.blue"
            :field="loadingProtocolField"
            :query="query"
            @change:searches="changeSearches"
          >
            <template #title>
              <div>
                Loading Protocol
                <info-tooltip>
                  <p>
                    This rectangle below displays the proportion of each loading protocol in the
                    database. See also the evolution of test data over the years on the right.
                  </p>
                  How to use?
                  <ul>
                    <li>
                      Filter the Database for a specific loading protocol type or dates by clicking
                      on the rectangle of using the dates sliders.
                    </li>
                  </ul>
                </info-tooltip>
              </div>
            </template>
          </hss-single-chart>
        </v-col>
        <v-col>
          <hss-single-chart
            :show-reset="true"
            :color="colors.deepPurple"
            :field="steelField"
            :query="query"
            @change:searches="changeSearches"
          >
            <template #title>
              <steel-type-card-title />
            </template>
          </hss-single-chart>
        </v-col>
      </v-row>
    </v-col>
  </v-row>
</template>
