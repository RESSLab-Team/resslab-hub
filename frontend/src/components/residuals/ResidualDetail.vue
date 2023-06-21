<script setup lang="ts">
import type { ResidualStressModel } from '@/backend'
import CommonDetail, { type DetailCarouselItem } from '@/components/commons/CommonDetail.vue'
import PropertyItem from '@/components/commons/PropertyItem.vue'
import { residualsApi } from '@/plugins/axios'
import { publicPath } from '@/utils/common'
import { formatNumber } from '@/utils/formatter'
import { inv, matrix, multiply } from 'mathjs'
import { ref, watch } from 'vue'

import type { LineSeriesOption } from 'echarts'

const props = defineProps<{
  residual: ResidualStressModel
}>()
const emit = defineEmits<{
  (e: 'close'): void
}>()

function linspace(start: number, end: number, n: number): number[] {
  const diff = end - start
  const step = diff / (n - 1)
  return Array(n)
    .fill(0)
    .map((_, i) => start + i * step)
}
const carouselItems = ref<DetailCarouselItem[][]>([])
const flangeData = ref<number[][]>([])
residualsApi
  .getResidualStressesDistributionF1(props.residual.id)
  .then((response) => (flangeData.value = response.data))
watch(
  () => props.residual,
  (residual) => {
    carouselItems.value = [
      [
        {
          count: residual.distribution_F1_count,
          promise: residualsApi
            .getResidualStressesQpCoefficient(residual.id)
            .then((response) => response.data)
            .then((series) => {
              const coeff = series.map((serie) => serie[0])
              console.log(coeff)

              const { h_over_b, h, A, b, tf, tw, fy_n } = residual

              const h0 = h - 2 * tf

              const h_b_norm_full = 2 * ((h_over_b - 0.95) / (3.04 - 0.95)) - 1
              const h_norm_full = 2 * ((h - 96) / (1090 - 96)) - 1
              const Area_norm_full = 2 * ((A - 1320) / (175000 - 1320)) - 1

              // Calculate coefficients a, c, d and b for the full model
              const coeff_a_full = 107 + 51 * h_b_norm_full + 20 * Area_norm_full
              const coeff_c_full = -(142 + 84 * h_b_norm_full)
              const coeff_d_full = ((coeff_a_full - coeff_c_full) / Math.pow(h - tf, 2)) * 4
              const coeff_b_full =
                (-(
                  2 * tf * b * coeff_a_full +
                  tw * (h - 2 * tf) * coeff_c_full +
                  ((tw * Math.pow(h - 2 * tf, 3)) / 12) * coeff_d_full
                ) /
                  (2 * tf * Math.pow(b, 3))) *
                12

              // Define the quadratic polynomial models for the flange and web in RS
              const QP_Model_full_flange_RS = (x: number) =>
                coeff_a_full + coeff_b_full * Math.pow(x - b / 2, 2)
              const QP_Model_full_web_RS = (y: number) =>
                coeff_c_full + coeff_d_full * Math.pow(y - h / 2, 2)

              // Define the quadratic polynomial models for the flange and web
              const QP_flange_RS = (x: number) => coeff[0] + coeff[1] * Math.pow(x - b / 2, 2)
              const QP_web_RS = (y: number) => coeff[2] + coeff[3] * Math.pow(y - h / 2, 2)

              // Define evenly spaced vectors x, y and their variants
              const x = linspace(0, b, 100)
              const x_mod = linspace(0, b, 3)
              const x1 = linspace(0, b / 2, 2)
              const x2 = linspace(b / 2, b, 2)
              const x3 = linspace(-b / 2, b / 2, 100)
              const x3_scatter = linspace(-b / 2, b / 2, 3)

              const y = linspace(0, h, 100)
              const y_mod = linspace(0, h, 3)
              const y1 = linspace(tf / 2, h / 2, 2)
              const y2 = linspace(h / 2, h - tf / 2, 2)
              const y3 = linspace(-(h - tf) / 2, (h - tf) / 2, 100)
              const y3_scatter = linspace(-(h - tf) / 2, (h - tf) / 2, 3)
              const y4 = linspace(tf / 2, h - tf / 2, 100)
              const y4_mod = linspace(tf / 2, h - tf / 2, 3)

              // Galambos and Ketter 1959
              const sigma_c_GK = -0.3 * fy_n
              const sigma_t_GK = -sigma_c_GK / (1 + ((h * tw) / (b * tf)) * (1 - (2 * tf) / h))

              // Define the stress functions GK_flange_RS1, GK_flange_RS2 and GK_web_RS
              const GK_flange_RS1 = (x1: number) =>
                (2 / b) * (sigma_t_GK - sigma_c_GK) * x1 + sigma_c_GK
              const GK_flange_RS2 = (x2: number) =>
                (2 / b) * (sigma_c_GK - sigma_t_GK) * x2 + 2 * sigma_t_GK - sigma_c_GK
              const GK_web_RS = sigma_t_GK

              // ECCS 1984

              let alpha = 0.5

              // Determine alpha based on h/b ratio
              if (h / b > 1.2) {
                alpha = 0.3
              }

              // Calculate sigma_t_ECCS and sigma_c_ECCS based on fy and alpha
              let sigma_t_ECCS = fy_n * alpha
              let sigma_c_ECCS = -fy_n * alpha

              // Define the stress functions for ECCS model
              const ECCS_flange_RS1 = (x1: number) =>
                (2 / b) * (sigma_t_ECCS - sigma_c_ECCS) * x1 + sigma_c_ECCS
              const ECCS_flange_RS2 = (x2: number) =>
                (2 / b) * (sigma_c_ECCS - sigma_t_ECCS) * x2 + 2 * sigma_t_ECCS - sigma_c_ECCS
              const ECCS_web_RS1 = (y1: number) =>
                (2 / h) * (sigma_c_ECCS - sigma_t_ECCS) * y1 + sigma_t_ECCS
              const ECCS_web_RS2 = (y2: number) =>
                (2 / h) * (sigma_t_ECCS - sigma_c_ECCS) * y2 + 2 * sigma_c_ECCS - sigma_t_ECCS

              // Young 1975

              // Calculate sigma values according to Young 1975 model
              let sigma_t_YOUNG = 100 * (0.7 + (h0 * tw) / (2 * b * tf))
              let sigma_c1_YOUNG = -165 * (1 - (h0 * tw) / (2.4 * b * tf))
              let sigma_c2_YOUNG = -100 * (1.5 + (h0 * tw) / (2.4 * b * tf))

              // Define the stress functions for Young model
              const YOUNG_flange_RS = (x3: number) =>
                (4 / Math.pow(b, 2)) * (sigma_c1_YOUNG - sigma_t_YOUNG) * Math.pow(x3, 2) +
                sigma_t_YOUNG
              const YOUNG_web_RS = (y3: number) =>
                (4 / Math.pow(h - tf, 2)) * (sigma_t_YOUNG - sigma_c2_YOUNG) * Math.pow(y3, 2) +
                sigma_c2_YOUNG

              // Salazai and Papp 2005

              // Define alpha_SP and calculate parameters af, aw, cf, and cw
              let alpha_SP = 0.35
              let af =
                (-alpha_SP *
                  fy_n *
                  (20 * Math.pow(b, 3) * tf +
                    48 * b * Math.pow(h0, 2) * tf +
                    4 * Math.pow(h0, 3) * tw)) /
                (Math.pow(b, 2) *
                  (2 * Math.pow(b, 3) * tf + 8 * b * Math.pow(h0, 2) * tf + Math.pow(h0, 3) * tw))
              let aw =
                (alpha_SP *
                  fy_n *
                  2 *
                  b *
                  tf *
                  (8 * Math.pow(b, 3) * tf +
                    9 * Math.pow(b, 2) * h0 * tw +
                    10 * Math.pow(h0, 3) * tw)) /
                (Math.pow(h0, 3) *
                  tw *
                  (2 * Math.pow(b, 3) * tf + 8 * b * Math.pow(h0, 2) * tf + Math.pow(h0, 3) * tw))
              let cf =
                (alpha_SP * fy_n * b * tf * (3 * Math.pow(b, 2) + 4 * Math.pow(h0, 2))) /
                (2 * Math.pow(b, 3) * tf + 8 * b * Math.pow(h0, 2) * tf + Math.pow(h0, 3) * tw)
              let cw =
                (-alpha_SP *
                  fy_n *
                  b *
                  tf *
                  (8 * Math.pow(b, 3) * tf +
                    3 * Math.pow(b, 2) * h0 * tw +
                    2 * Math.pow(h0, 3) * tw)) /
                (2 *
                  h0 *
                  tw *
                  (2 * Math.pow(b, 3) * tf + 8 * b * Math.pow(h0, 2) * tf + Math.pow(h0, 3) * tw))

              // Define the stress functions for Salazai and Papp model
              let SP_flange_RS = (x3: number) => cf + af * Math.pow(x3, 2)
              let SP_web_RS = (y3: number) => cw + aw * Math.pow(y3, 2)

              // Bradford and Trahair 1985
              // Define matrix and vector for Bradford and Trahair 1985 model
              let MAT_A = matrix([
                [1, 0, 0, 0, 0],
                [0, 1, 0, 0, 0],
                [0, 0, 1, 1, 1],
                [0, 0, 1, 1 / 3, 1 / 5],
                [0, 0, 1 / 3, 1 / 5, 1 / 7]
              ])
              let Af_Aw: number = (2 * b * tf) / (h0 * tw)
              let VECT_b = matrix([
                [1 / 2],
                [17 / 20],
                [1 / 2],
                [(-13 / 60) * Af_Aw],
                [(Af_Aw * (Math.pow(b, 2) - 11 * Math.pow(h0 + tf, 2))) / (300 * Math.pow(h0, 2))]
              ])

              // Solve system to get coefficients
              let coeff_BT = multiply(inv(MAT_A), VECT_b)

              // Define the stress functions for Bradford and Trahair model
              let BT_flange_RS = (x3: number) =>
                fy_n * (coeff_BT.get([0, 0]) - coeff_BT.get([1, 0]) * Math.pow((2 * x3) / b, 2))
              let BT_web_RS = (y3: number) =>
                fy_n *
                (coeff_BT.get([2, 0]) +
                  coeff_BT.get([3, 0]) * Math.pow((2 * y3) / (h - tf), 2) +
                  coeff_BT.get([4, 0]) * Math.pow((2 * y3) / (h - tf), 4))

              console.log({ fy_n, sigma_t_GK, sigma_c_GK, b, h, tw, tf })
              return [
                {
                  name: 'Galambos and Ketter 1959',
                  data: x1
                    .map((x) => [x - b / 2, GK_flange_RS1(x)])
                    .concat(x2.map((x) => [x - b / 2, GK_flange_RS2(x)]))
                },
                {
                  name: 'ECCS 1984',
                  data: x1
                    .map((x) => [x - b / 2, ECCS_flange_RS1(x)])
                    .concat(x2.map((x) => [x - b / 2, ECCS_flange_RS2(x)]))
                },
                {
                  name: 'Young 1975',
                  data: x3.map((x) => [x, YOUNG_flange_RS(x)])
                },
                {
                  name: 'Salazai and Papp 2005',
                  data: x3.map((x) => [x, SP_flange_RS(x)])
                },
                {
                  name: 'Bradford and Trahair 1985',
                  data: x3.map((x) => [x, BT_flange_RS(x)])
                },
                {
                  name: 'QP Model full flange',
                  data: x.map((x) => [x, QP_Model_full_flange_RS(x)])
                },
                {
                  name: 'Measured residual stresses',
                  data: flangeData.value.map((x) => [x[0], x[1]])
                }
              ] as LineSeriesOption[]
            }),
          title: 'Stress Strain',
          xAxisName: 'ε',
          yAxisName: 'σ 0,f [MPa]'
        }
      ]
    ]
  },
  {
    immediate: true
  }
)
</script>

<template>
  <common-detail
    :reference="residual.reference"
    :link="residual.link"
    :carousel-items="carouselItems"
    :carousel-height="400"
    @close="emit('close')"
  >
    <template #title>
      {{ residual.experimental_program }} ({{ residual.date }}) -
      {{ residual.profile }}
    </template>
    <template #body>
      <v-row>
        <v-col class="mt-6" cols="6">
          <h2 class="mb-2">Structural Steel Element</h2>
          <p class="mb-6">
            <property-item name="Profile type">
              {{ residual.profile_type }}
            </property-item>
            <property-item name="Cross section">
              {{ residual.profile }}
            </property-item>
          </p>
          <h2 class="mb-2">Steel Material Designation</h2>
          <p class="mb-6">
            <property-item name="Steel type">
              {{ residual.steel }}
            </property-item>
            <property-item name="Nominal yield stress" unit="MPa">
              {{ formatNumber(residual.fy_n) }}
            </property-item>
            <property-item name="Expected yield stress" unit="MPa">
              {{ formatNumber(residual.fy_e) }}
            </property-item>
            <property-item name="Measured yield stress (flange)" unit="MPa">
              {{ formatNumber(residual.fy_mf) }}
            </property-item>
            <property-item name="Measured yield stress (web)" unit="MPa">
              {{ formatNumber(residual.fy_mw) }}
            </property-item>
          </p>
          <h2 class="mb-2">Cross-Sectional Geometric Properties</h2>
          <p class="mb-6">
            <property-item name="Height of the cross section" unit="mm">
              {{ formatNumber(residual.h) }}
            </property-item>
            <property-item name="Width of the cross section" unit="mm">
              {{ formatNumber(residual.b) }}
            </property-item>
            <property-item name="Web thickness of the cross section" unit="mm">
              {{ formatNumber(residual.tw) }}
            </property-item>
            <property-item name="Flange thickness of the cross section" unit="mm">
              {{ formatNumber(residual.tf) }}
            </property-item>
            <property-item name="Fillet radii of the cross section" unit="mm">
              {{ formatNumber(residual.r) }}
            </property-item>
            <property-item name="Area of the cross section" unit="mm">
              {{ formatNumber(residual.A) }}
            </property-item>
          </p>
        </v-col>
        <v-col cols="6">
          <v-img :src="publicPath + 'img/residuals/detail.png'" />
        </v-col>
      </v-row>
    </template>
  </common-detail>
</template>
