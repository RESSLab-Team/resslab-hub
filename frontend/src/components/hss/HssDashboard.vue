<script setup lang="ts">
import { HSSColumnField, type HSSColumnModel } from '@/backend'
import InfoTooltip from '@/components/commons/InfoTooltip.vue'

import HssTable from '@/components/hss/HssTable.vue'
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
        <v-col cols="12"> </v-col>
      </v-row>
    </v-col>
    <v-col md="6">
      <v-row v-if="item">
        <v-col cols="12"> </v-col>
      </v-row>
      <v-row v-else>
        <v-col cols="12">
          <v-card>
            <v-card-title class="d-flex justify-space-between"> Profile </v-card-title>
            <v-card-text>
              <v-row>
                <v-col cols="12" md="6"> </v-col>
                <v-col cols="12" md="6"> </v-col>
              </v-row>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12"> </v-col>
      </v-row>
    </v-col>
  </v-row>
</template>
