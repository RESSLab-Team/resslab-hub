<script setup lang="ts">
import { TensileCouponField, type TensileCouponModel } from '@/backend'
import InfoTooltip from '@/components/commons/InfoTooltip.vue'
import ResetChartButton from '@/components/commons/ResetChartButton.vue'
import SteelTypeCardTitle from '@/components/commons/SteelTypeCardTitle.vue'
import TensileCouponDoubleChart from '@/components/tensile-coupons/charts/TensileCouponDoubleChart.vue'
import TensileCouponParallelChart from '@/components/tensile-coupons/charts/TensileCouponParallelChart.vue'
import TensileCouponSingleChart from '@/components/tensile-coupons/charts/TensileCouponSingleChart.vue'
import TensileCouponTable from '@/components/tensile-coupons/TensileCouponTable.vue'

import type { DoubleFields, ParallelField } from '@/composables/chart'
import { useDashboard } from '@/composables/dashboard'
import { useRoute, useRouter } from 'vue-router'
import colors from 'vuetify/lib/util/colors'

const route = useRoute()
const router = useRouter()
const { clickTableRow, item, query, search, searches, changeSearches, updatePage } =
  useDashboard<TensileCouponModel>(route, router, TensileCouponField)

const parallelFields: ParallelField<TensileCouponField>[] = [
  { id: TensileCouponField.SteelGrade },
  { id: TensileCouponField.YieldStress02Mpa },
  {
    id: {
      dividend: TensileCouponField.TensileStrengthMpa,
      divisor: TensileCouponField.YieldStress02Mpa
    }
  },
  {
    id: {
      dividend: TensileCouponField.YieldStress02Mpa,
      divisor: TensileCouponField.FyNMpa
    }
  },
  { id: TensileCouponField.ElongationAtFracture },
  { id: TensileCouponField.ReductionOfArea },
  { id: TensileCouponField.AvgInitReducedThicknessMm }
]
const profileYearFields: DoubleFields<TensileCouponField> = [
  TensileCouponField.Year,
  TensileCouponField.ProfileType
]
const profileThicknessFields: DoubleFields<TensileCouponField> = [
  TensileCouponField.AvgInitReducedThicknessMm,
  TensileCouponField.ProfileType
]
const steelField = TensileCouponField.SteelGrade

const profileTypeFields: TensileCouponField[] = [
  TensileCouponField.Year,
  TensileCouponField.ProfileType,
  TensileCouponField.AvgInitReducedThicknessMm,
  TensileCouponField.ProfileType
]
</script>

<template>
  <v-row>
    <v-col md="6">
      <v-row>
        <v-col cols="12">
          <tensile-coupon-table
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
          <tensile-coupon-parallel-chart
            :color="colors.orange"
            :fields="parallelFields"
            :query="query"
            @change:searches="changeSearches"
          >
            <template #title>
              <info-tooltip>Parallel Axis</info-tooltip>
            </template>
          </tensile-coupon-parallel-chart>
        </v-col>
      </v-row>
    </v-col>
    <v-col md="6">
      <v-row v-if="item">
        <v-col cols="12">
          <!-- Detail panel added in Commit 7 -->
        </v-col>
      </v-row>
      <v-row v-else>
        <v-col cols="12">
          <v-card>
            <v-card-title class="d-flex justify-space-between">
              Profile Type
              <reset-chart-button
                :field="profileTypeFields"
                :is-filtered="profileTypeFields.some(field => query.includes((field as string)))"
                @change:searches="changeSearches"
              />
            </v-card-title>
            <v-card-text>
              <v-row>
                <v-col cols="12" md="6">
                  <tensile-coupon-double-chart
                    :fields="profileYearFields"
                    :query="query"
                    type="line"
                    @change:searches="changeSearches"
                  />
                </v-col>
                <v-col cols="12" md="6">
                  <tensile-coupon-double-chart
                    :fields="profileThicknessFields"
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
          <tensile-coupon-single-chart
            :color="colors.deepPurple"
            :field="steelField"
            :query="query"
            @change:searches="changeSearches"
          >
            <template #title>
              <steel-type-card-title />
            </template>
          </tensile-coupon-single-chart>
        </v-col>
      </v-row>
    </v-col>
  </v-row>
</template>
