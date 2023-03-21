<script setup lang="ts">
import { ResidualStressField, type ResidualStressModel } from '@/backend'
import InfoTooltip from '@/components/commons/InfoTooltip.vue'
import ResidualDoubleChart from '@/components/residuals/charts/ResidualDoubleChart.vue'
import ResidualParallelChart from '@/components/residuals/charts/ResidualParallelChart.vue'
import ResidualSingleChart from '@/components/residuals/charts/ResidualSingleChart.vue'
import ResidualTable from '@/components/residuals/ResidualTable.vue'
import type { DoubleFields, ParallelField } from '@/composables/chart'
import { useDashboard } from '@/composables/dashboard'
import { useRoute } from 'vue-router'
import colors from 'vuetify/lib/util/colors'

const route = useRoute()
const { item, query, search, searches, changeSearches, updatePage } =
  useDashboard<ResidualStressModel>(route, ResidualStressField)

const parallelFields: ParallelField<ResidualStressField>[] = [
  { id: ResidualStressField.Date },
  { id: ResidualStressField.Profile }
]
const profileFields: DoubleFields<ResidualStressField> = [
  ResidualStressField.Date,
  ResidualStressField.Profile
]
const steelField = ResidualStressField.Profile
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
          <!-- TODO detail -->
        </v-col>
      </v-row>
      <v-row v-else>
        <v-col cols="12">
          <v-card>
            <v-card-title>Profile Type</v-card-title>
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
              </v-row>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12">
          <v-card>
            <v-card-title>Profile Type</v-card-title>
            <v-card-text>
              <residual-single-chart
                :color="colors.deepPurple"
                :field="steelField"
                :query="query"
                @change:searches="changeSearches"
              />
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-col>
  </v-row>
</template>
