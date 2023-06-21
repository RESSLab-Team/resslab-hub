<script setup lang="ts">
import type { ResidualStressModel } from '@/backend'
import CommonDetail, { type DetailCarouselItem } from '@/components/commons/CommonDetail.vue'
import PropertyItem from '@/components/commons/PropertyItem.vue'
import { residualsApi } from '@/plugins/axios'
import { publicPath } from '@/utils/common'
import { formatNumber } from '@/utils/formatter'
import { ref, watch } from 'vue'

import { createLineSeries } from '@/utils/residual'
import type { LineSeriesOption } from 'echarts'

const props = defineProps<{
  residual: ResidualStressModel
}>()
const emit = defineEmits<{
  (e: 'close'): void
}>()

const carouselItems = ref<DetailCarouselItem[][]>([])

const promise = ref<
  Promise<{
    flangeSeries: LineSeriesOption[]
    webSeries: LineSeriesOption[]
  }>
>(Promise.resolve({ flangeSeries: [], webSeries: [] }))

watch(
  () => props.residual,
  (residual) => {
    promise.value = Promise.all([
      residualsApi.getResidualStressesQpCoefficient(residual.id),
      residualsApi.getResidualStressesDistributionF1(props.residual.id),
      residualsApi.getResidualStressesDistributionF2(props.residual.id),
      residualsApi.getResidualStressesDistributionW1(props.residual.id)
    ])
      .then((responses) => responses.map((response) => response.data))
      .then(([qpCoefficients, distributionF1, distributionF2, distributionW1]) => {
        const lines = createLineSeries(
          props.residual,
          qpCoefficients,
          distributionF1,
          distributionW1,
          distributionF2
        )
        return lines
      })
  },
  {
    immediate: true
  }
)

watch(
  () => promise.value,
  (newPromise) => {
    carouselItems.value = [
      [
        {
          noCount: true,
          promise: newPromise.then(({ flangeSeries }) => flangeSeries),
          title: 'Stress Strain bf',
          xAxisName: 'bf',
          yAxisName: 'σ 0,f [MPa]'
        }
      ],
      [
        {
          noCount: true,
          promise: newPromise.then(({ webSeries }) => webSeries),
          title: 'Stress Strain h',
          axisPointerType: 'y',
          xAxisName: 'σ 0,w [MPa]',
          yAxisName: 'h'
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
    :carousel-height="600"
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
