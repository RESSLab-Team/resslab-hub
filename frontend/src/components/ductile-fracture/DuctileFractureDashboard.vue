<script setup lang="ts">
import { DuctileFractureField, type DuctileFractureModel } from '@/backend'
import InfoTooltip from '@/components/commons/InfoTooltip.vue'
import ResetChartButton from '@/components/commons/ResetChartButton.vue'
import SteelTypeCardTitle from '@/components/commons/SteelTypeCardTitle.vue'
import DuctileFractureDoubleChart from '@/components/ductile-fracture/charts/DuctileFractureDoubleChart.vue'
import DuctileFractureParallelChart from '@/components/ductile-fracture/charts/DuctileFractureParallelChart.vue'
import DuctileFractureSingleChart from '@/components/ductile-fracture/charts/DuctileFractureSingleChart.vue'
import DuctileFractureDetail from '@/components/ductile-fracture/DuctileFractureDetail.vue'
import DuctileFractureTable from '@/components/ductile-fracture/DuctileFractureTable.vue'

import type { DoubleFields, ParallelField } from '@/composables/chart'
import { useDashboard } from '@/composables/dashboard'
import { useRoute, useRouter } from 'vue-router'
import colors from 'vuetify/lib/util/colors'

const route = useRoute()
const router = useRouter()
const { clickTableRow, closeDetail, item, query, search, searches, changeSearches, updatePage } =
  useDashboard<DuctileFractureModel>(route, router, DuctileFractureField)

const parallelFields: ParallelField<DuctileFractureField>[] = [
  { id: DuctileFractureField.SteelType },
  { id: DuctileFractureField.FYn },
  { id: DuctileFractureField.SpecimenType },
  { id: DuctileFractureField.NomNotchRadius },
  { id: DuctileFractureField.LodeAvgTillFr },
  { id: DuctileFractureField.TriaxAvgTillFr },
  { id: DuctileFractureField.PeeqAtFr },
  { id: DuctileFractureField.LocationCoupon },
  {
    id: {
      key: 'cev',
      fields: [
        DuctileFractureField.ChemicalCompositionC,
        DuctileFractureField.ChemicalCompositionMn,
        DuctileFractureField.ChemicalCompositionSi,
        DuctileFractureField.ChemicalCompositionCr,
        DuctileFractureField.ChemicalCompositionMo,
        DuctileFractureField.ChemicalCompositionV,
        DuctileFractureField.ChemicalCompositionNi,
        DuctileFractureField.ChemicalCompositionCu
      ],
      compute: ([c, mn, si, cr, mo, v, ni, cu]) =>
        [c, mn, si, cr, mo, v, ni, cu].some((x) => x == null)
          ? null
          : c! + mn! / 6 + si! / 6 + (cr! + mo! + v!) / 5 + (ni! + cu!) / 15
    }
  }
]
const dateSpecimenFields: DoubleFields<DuctileFractureField> = [
  DuctileFractureField.Date,
  DuctileFractureField.SpecimenType
]
const triaxSpecimenFields: DoubleFields<DuctileFractureField> = [
  DuctileFractureField.TriaxAvgTillFr,
  DuctileFractureField.SpecimenType
]
const lodeSpecimenFields: DoubleFields<DuctileFractureField> = [
  DuctileFractureField.LodeAvgTillFr,
  DuctileFractureField.SpecimenType
]
const steelField = DuctileFractureField.SteelType

const specimenTypeCardFields: DuctileFractureField[] = [
  DuctileFractureField.SpecimenType,
  DuctileFractureField.Date
]
const specimenCardFields: DuctileFractureField[] = [
  DuctileFractureField.TriaxAvgTillFr,
  DuctileFractureField.SpecimenType,
  DuctileFractureField.LodeAvgTillFr,
  DuctileFractureField.SpecimenType
]
</script>

<template>
  <v-row>
    <v-col md="6">
      <v-row>
        <v-col cols="12">
          <ductile-fracture-table
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
          <ductile-fracture-parallel-chart
            :color="colors.orange"
            :fields="parallelFields"
            :query="query"
            @change:searches="changeSearches"
          >
            <template #title>
              <info-tooltip>Parallel Axis</info-tooltip>
            </template>
          </ductile-fracture-parallel-chart>
        </v-col>
      </v-row>
    </v-col>
    <v-col md="6">
      <v-row v-if="item">
        <v-col cols="12">
          <ductile-fracture-detail :ductile-fracture="item" @close="closeDetail" />
        </v-col>
      </v-row>
      <v-row v-else>
        <v-col cols="12">
          <v-card>
            <v-card-title class="d-flex justify-space-between">
              Specimen Type
              <reset-chart-button
                :field="specimenTypeCardFields"
                :is-filtered="specimenTypeCardFields.some(field => query.includes((field as string)))"
                @change:searches="changeSearches"
              />
            </v-card-title>
            <v-card-text>
              <v-row>
                <v-col cols="12" md="6">
                  <ductile-fracture-single-chart
                    :field="DuctileFractureField.SpecimenType"
                    :query="query"
                    :show-reset="false"
                    flat
                    @change:searches="changeSearches"
                  />
                </v-col>
                <v-col cols="12" md="6">
                  <ductile-fracture-double-chart
                    :fields="dateSpecimenFields"
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
          <v-card>
            <v-card-title class="d-flex justify-space-between">
              Specimen
              <reset-chart-button
                :field="specimenCardFields"
                :is-filtered="specimenCardFields.some(field => query.includes((field as string)))"
                @change:searches="changeSearches"
              />
            </v-card-title>
            <v-card-text>
              <v-row>
                <v-col cols="12" md="6">
                  <ductile-fracture-double-chart
                    :fields="triaxSpecimenFields"
                    :query="query"
                    type="bar"
                    @change:searches="changeSearches"
                  />
                </v-col>
                <v-col cols="12" md="6">
                  <ductile-fracture-double-chart
                    :fields="lodeSpecimenFields"
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
          <ductile-fracture-single-chart
            :color="colors.deepPurple"
            :field="steelField"
            :query="query"
            @change:searches="changeSearches"
          >
            <template #title>
              <steel-type-card-title />
            </template>
          </ductile-fracture-single-chart>
        </v-col>
      </v-row>
    </v-col>
  </v-row>
</template>
