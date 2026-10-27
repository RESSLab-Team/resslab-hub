<script setup lang="ts">
import type { ResidualStressModel } from '@/backend'
import CommonDetail, { type DetailCarouselItem } from '@/components/commons/CommonDetail.vue'
import PropertyItem from '@/components/commons/PropertyItem.vue'
import { residualsApi } from '@/plugins/axios'
import { publicPath } from '@/utils/common'
import { formatNumber } from '@/utils/formatter'
import { computed, ref, watch } from 'vue'

import { createLineSeries, validateResidualModelParams } from '@/utils/residual'
import type { LineSeriesOption } from 'echarts'
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })

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

const hasValidParameters = computed(() => validateResidualModelParams(props.residual))

const errorMessage = ref('')

watch(
  () => props.residual,
  (residual) => {
    if (!hasValidParameters.value) {
      errorMessage.value = t('detail.residual.error_message')
      return Promise.resolve()
    } else {
      errorMessage.value = ''
    }

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
    newPromise.then(
      ({
        flangeSeries,
        webSeries
      }: {
        flangeSeries: LineSeriesOption[]
        webSeries: LineSeriesOption[]
      }) => {
        carouselItems.value = [
          [
            {
              noCount: true,
              series: flangeSeries,
              title: t('detail.residual.flange_distribution'),
              xAxisName: 'bf [mm]',
              yAxisName: 'σ 0,f [MPa]'
            }
          ],
          [
            {
              noCount: true,
              series: webSeries,
              title: t('detail.residual.web_distribution'),
              axisPointerType: 'y',
              xAxisName: 'σ 0,w [MPa]',
              yAxisName: 'h [mm]'
            }
          ]
        ]
      }
    )
  },
  {
    immediate: true
  }
)
</script>

<template>
  <common-detail
    database-id="residuals"
    :record="residual"
    :reference="residual.reference"
    :link="residual.link"
    :carousel-items="hasValidParameters ? carouselItems : []"
    :carousel-height="600"
    @close="emit('close')"
  >
    <template #title>
      {{ residual.experimental_program }} ({{ residual.date }}) -
      {{ residual.profile }}
    </template>
    <template #body>
      <v-alert v-if="errorMessage" class="my-10" variant="outlined" type="warning">{{
        errorMessage
      }}</v-alert>

      <v-row>
        <v-col class="mt-6" cols="12" sm="6">
          <h2 class="mb-2">{{ $t('detail.residual.structural_steel_element') }}</h2>
          <p class="mb-6">
            <property-item :name="$t('detail.residual.profile_type')">
              {{ residual.profile_type }}
            </property-item>
            <property-item :name="$t('detail.residual.cross_section')">
              {{ residual.profile }}
            </property-item>
          </p>
          <h2 class="mb-2">{{ $t('detail.residual.steel_material_designation') }}</h2>
          <p class="mb-6">
            <property-item :name="$t('detail.residual.steel_type')">
              {{ residual.steel }}
            </property-item>
            <property-item :name="$t('detail.residual.nominal_yield_stress')" unit="MPa">
              {{ formatNumber(residual.fy_n) }}
            </property-item>
            <property-item :name="$t('detail.residual.expected_yield_stress')" unit="MPa">
              {{ formatNumber(residual.fy_e) }}
            </property-item>
            <property-item :name="$t('detail.residual.measured_yield_stress_flange')" unit="MPa">
              {{ formatNumber(residual.fy_mf) }}
            </property-item>
            <property-item :name="$t('detail.residual.measured_yield_stress_web')" unit="MPa">
              {{ formatNumber(residual.fy_mw) }}
            </property-item>
          </p>
          <h2 class="mb-2">{{ $t('detail.residual.cross_sectional_geometric_properties') }}</h2>
          <p class="mb-6">
            <property-item :name="$t('detail.residual.height_of_the_cross_section')" unit="mm">
              {{ formatNumber(residual.h) }}
            </property-item>
            <property-item :name="$t('detail.residual.width_of_the_cross_section')" unit="mm">
              {{ formatNumber(residual.b) }}
            </property-item>
            <property-item
              :name="$t('detail.residual.web_thickness_of_the_cross_section')"
              unit="mm"
            >
              {{ formatNumber(residual.tw) }}
            </property-item>
            <property-item
              :name="$t('detail.residual.flange_thickness_of_the_cross_section')"
              unit="mm"
            >
              {{ formatNumber(residual.tf) }}
            </property-item>
            <property-item
              :name="$t('detail.residual.fillet_radii_of_the_cross_section')"
              unit="mm"
            >
              {{ formatNumber(residual.r) }}
            </property-item>
            <property-item :name="$t('detail.residual.area_of_the_cross_section')" unit="mm">
              {{ formatNumber(residual.A) }}
            </property-item>
          </p>
        </v-col>
        <v-col cols="12" sm="6">
          <v-img :src="publicPath + 'img/residuals/detail.png'" />
        </v-col>
      </v-row>
    </template>
  </common-detail>
</template>
