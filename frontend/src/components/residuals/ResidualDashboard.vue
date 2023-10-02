<script setup lang="ts">
import { ResidualStressField, type ResidualStressModel } from '@/backend'
import InfoTooltip from '@/components/commons/InfoTooltip.vue'
import ResidualDoubleChart from '@/components/residuals/charts/ResidualDoubleChart.vue'
import ResidualParallelChart from '@/components/residuals/charts/ResidualParallelChart.vue'
import ResidualSingleChart from '@/components/residuals/charts/ResidualSingleChart.vue'
import ResidualDetail from '@/components/residuals/ResidualDetail.vue'
import ResidualTable from '@/components/residuals/ResidualTable.vue'
import SteelTypeCardTitle from '@/components/commons/SteelTypeCardTitle.vue'
import ResetChartButton from '@/components/commons/ResetChartButton.vue'

import type { DoubleFields, ParallelField } from '@/composables/chart'
import { useDashboard } from '@/composables/dashboard'
import { useRoute } from 'vue-router'
import colors from 'vuetify/lib/util/colors'

const route = useRoute()
const { clickTableRow, closeDetail, item, query, search, searches, changeSearches, updatePage } =
  useDashboard<ResidualStressModel>(route, ResidualStressField)

const parallelFields: ParallelField<ResidualStressField>[] = [
  { id: ResidualStressField.Steel, name: 'Steel Grade' },
  { id: ResidualStressField.HOverB, name: 'h/bf' },
  { id: ResidualStressField.Tf, name: 'tf [mm]' },
  { id: ResidualStressField.A, name: 'A [mm²]' },
  { id: ResidualStressField.Sigma0F, name: 'σ0,f [MPa]' },
  { id: ResidualStressField.Sigma0W, name: 'σ0,w [MPa] ' }
]
const profileFields: DoubleFields<ResidualStressField> = [
  ResidualStressField.Date,
  ResidualStressField.ProfileType
]

const profileFieldsReset: ResidualStressField[] = [
  ResidualStressField.Date,
  ResidualStressField.ProfileType,
  ResidualStressField.H,
  ResidualStressField.ProfileType
]

const steelField = ResidualStressField.Steel
</script>

<template>
  <v-row>
    <v-col md="6">
      <v-row>
        <v-col cols="12">
          <residual-table
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
          <residual-parallel-chart
            :color="colors.orange"
            :fields="parallelFields"
            :query="query"
            @change:searches="changeSearches"
          >
            <template #title>
              <info-tooltip>Parallel Axis</info-tooltip>
            </template>
          </residual-parallel-chart>
        </v-col>
      </v-row>
    </v-col>
    <v-col md="6">
      <v-row v-if="item">
        <v-col cols="12">
          <residual-detail :residual="item" @close="closeDetail" />
        </v-col>
      </v-row>
      <v-row v-else>
        <v-col cols="12">
          <v-card>
            <v-card-title class="d-flex justify-space-between">
              Profile
              <reset-chart-button
                :field="profileFieldsReset"
                :is-filtered="profileFieldsReset.some(field => query.includes((field as string)))"
                @change:searches="changeSearches"
              />
            </v-card-title>
            <v-card-text>
              <v-row>
                <v-col cols="12" md="6">
                  <residual-double-chart
                    :fields="profileFields"
                    :query="query"
                    type="line"
                    @change:searches="changeSearches"
                  />
                </v-col>
                <v-col cols="12" md="6">
                  <residual-double-chart
                    :fields="[ResidualStressField.H, ResidualStressField.ProfileType]"
                    :query="query"
                    type="bar"
                    @change:searches="changeSearches"
                  />
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12">
          <residual-single-chart
            :color="colors.deepPurple"
            :field="steelField"
            :query="query"
            @change:searches="changeSearches"
          >
            <template #title>
              <steel-type-card-title />
            </template>
          </residual-single-chart>
        </v-col>
      </v-row>
    </v-col>
  </v-row>
</template>
