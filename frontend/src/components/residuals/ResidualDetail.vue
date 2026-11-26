<script setup lang="ts">
import type { ResidualStressModel } from '@/backend'
import CommonDetail, { type DetailCarouselItem } from '@/components/commons/CommonDetail.vue'
import PropertyItem from '@/components/commons/PropertyItem.vue'
import ZoomableImage from '@/components/commons/ZoomableImage.vue'
import { residualsApi } from '@/plugins/axios'
import { useRecordFormat } from '@/composables/useRecordFormat'
import { getResidualStressSchematic } from '@/utils/component'
import type { FieldGroupId } from '@/utils/fieldGroups'
import { computed, ref, watch } from 'vue'

import { createLineSeries, validateResidualModelParams } from '@/utils/residual'
import {
  createBuiltUpLineSeries,
  isBuiltUp,
  isMonosymmetric,
  type BuiltUpRecord
} from '@/utils/residualBuiltUp'
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })

const props = defineProps<{
  residual: ResidualStressModel
}>()

const formatNumber = useRecordFormat('residuals')
const emit = defineEmits<{
  (e: 'close'): void
}>()

const carouselItems = ref<DetailCarouselItem[][]>([])

// Built-up sections (#228) have their own models, sketches and rows.
const record = computed(() => props.residual as unknown as BuiltUpRecord)
const builtUp = computed(() => isBuiltUp(record.value))
const mono = computed(() => builtUp.value && isMonosymmetric(record.value))

// The hot-rolled models need the whole section and fy_n. A built-up record
// draws whatever it has: each model leaves itself out when an input is missing.
const hasValidParameters = computed(
  () => builtUp.value || validateResidualModelParams(props.residual)
)

// The welding and plate cutting only exist for a built-up section.
const hiddenGroups = computed<FieldGroupId[]>(() => (builtUp.value ? [] : ['fabrication_details']))

const errorMessage = ref('')

function hotRolledItems(residual: ResidualStressModel): Promise<DetailCarouselItem[][]> {
  return Promise.all([
    residualsApi.getResidualStressesQpCoefficient(residual.id),
    residualsApi.getResidualStressesDistributionF1(residual.id),
    residualsApi.getResidualStressesDistributionF2(residual.id),
    residualsApi.getResidualStressesDistributionW1(residual.id)
  ])
    .then((responses) => responses.map((response) => response.data))
    .then(([qpCoefficients, distributionF1, distributionF2, distributionW1]) => {
      const { flangeSeries, webSeries } = createLineSeries(
        residual,
        qpCoefficients,
        distributionF1,
        distributionW1,
        distributionF2
      )
      return [
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
    })
}

function builtUpItems(residual: ResidualStressModel): Promise<DetailCarouselItem[][]> {
  return Promise.all([
    residualsApi.getResidualStressesQpParameters(residual.id).then((response) => response.data),
    residualsApi.getResidualStressesDistributionF1(residual.id).then((response) => response.data),
    residualsApi.getResidualStressesDistributionF2(residual.id).then((response) => response.data),
    residualsApi.getResidualStressesDistributionW1(residual.id).then((response) => response.data)
  ]).then(([qpParameters, distributionF1, distributionF2, distributionW1]) => {
    const series = createBuiltUpLineSeries(
      residual as unknown as BuiltUpRecord,
      qpParameters,
      distributionF1,
      distributionF2,
      distributionW1
    )
    const web: DetailCarouselItem = {
      noCount: true,
      series: series.web,
      title: t('detail.residual.web_distribution'),
      axisPointerType: 'y',
      xAxisName: 'σ 0,w [MPa]',
      yAxisName: 'h [mm]'
    }
    const pages: DetailCarouselItem[] = series.separateFlanges
      ? [
          {
            noCount: true,
            series: series.flange1,
            title: t('detail.residual.flange_1_distribution'),
            xAxisName: 'bf,top [mm]',
            yAxisName: 'σ 0,f [MPa]'
          },
          {
            noCount: true,
            series: series.flange2,
            title: t('detail.residual.flange_2_distribution'),
            xAxisName: 'bf,bot [mm]',
            yAxisName: 'σ 0,b,f [MPa]'
          },
          web
        ]
      : [
          {
            noCount: true,
            series: series.flange1,
            title: t('detail.residual.flange_distribution'),
            xAxisName: 'bf [mm]',
            yAxisName: 'σ 0,f [MPa]'
          },
          web
        ]
    // A chart with nothing to draw (no measurement and no model) is left out.
    return pages.filter((page) => (page.series?.length ?? 0) > 0).map((page) => [page])
  })
}

watch(
  () => props.residual,
  (residual) => {
    carouselItems.value = []
    if (!hasValidParameters.value) {
      errorMessage.value = t('detail.residual.error_message')
      return
    }
    errorMessage.value = ''
    const shown = residual.id
    ;(builtUp.value ? builtUpItems(residual) : hotRolledItems(residual)).then((items) => {
      // Another record opened in the meantime: its own request fills the charts.
      if (props.residual.id === shown) carouselItems.value = items
    })
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
    :hidden-groups="hiddenGroups"
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
            <property-item column="profile_type" :name="$t('detail.residual.profile_type')">
              {{ residual.profile_type }}
            </property-item>
            <property-item column="profile" :name="$t('detail.residual.cross_section')">
              {{ residual.profile }}
            </property-item>
            <property-item v-if="builtUp" column="sym" :name="$t('detail.residual.symmetry')">
              {{
                mono ? $t('detail.residual.symmetry_mono') : $t('detail.residual.symmetry_doubly')
              }}
            </property-item>
          </p>
          <h2 class="mb-2">{{ $t('detail.residual.steel_material_designation') }}</h2>
          <p class="mb-6">
            <property-item column="steel" :name="$t('detail.residual.steel_type')">
              {{ residual.steel }}
            </property-item>
            <property-item
              column="fy_n"
              :name="$t('detail.residual.nominal_yield_stress')"
              unit="MPa"
            >
              {{ formatNumber(residual, 'fy_n') }}
            </property-item>
            <property-item
              column="fy_e"
              :name="$t('detail.residual.expected_yield_stress')"
              unit="MPa"
            >
              {{ formatNumber(residual, 'fy_e') }}
            </property-item>
            <property-item
              column="fy_mf"
              :name="$t('detail.residual.measured_yield_stress_flange')"
              unit="MPa"
            >
              {{ formatNumber(residual, 'fy_mf') }}
            </property-item>
            <property-item
              column="fy_mw"
              :name="$t('detail.residual.measured_yield_stress_web')"
              unit="MPa"
            >
              {{ formatNumber(residual, 'fy_mw') }}
            </property-item>
          </p>
          <h2 class="mb-2">{{ $t('detail.residual.cross_sectional_geometric_properties') }}</h2>
          <p class="mb-6">
            <property-item
              column="h"
              :name="$t('detail.residual.height_of_the_cross_section')"
              unit="mm"
            >
              {{ formatNumber(residual, 'h') }}
            </property-item>
            <property-item
              column="b"
              :name="
                mono
                  ? $t('detail.residual.width_of_flange_f1')
                  : $t('detail.residual.width_of_the_cross_section')
              "
              unit="mm"
            >
              {{ formatNumber(residual, 'b') }}
            </property-item>
            <property-item
              v-if="mono"
              column="b2"
              :name="$t('detail.residual.width_of_flange_f2')"
              unit="mm"
            >
              {{ formatNumber(residual, 'b2') }}
            </property-item>
            <property-item
              column="tw"
              :name="$t('detail.residual.web_thickness_of_the_cross_section')"
              unit="mm"
            >
              {{ formatNumber(residual, 'tw') }}
            </property-item>
            <property-item
              column="tf"
              :name="
                mono
                  ? $t('detail.residual.thickness_of_flange_f1')
                  : $t('detail.residual.flange_thickness_of_the_cross_section')
              "
              unit="mm"
            >
              {{ formatNumber(residual, 'tf') }}
            </property-item>
            <property-item
              v-if="mono"
              column="tf2"
              :name="$t('detail.residual.thickness_of_flange_f2')"
              unit="mm"
            >
              {{ formatNumber(residual, 'tf2') }}
            </property-item>
            <property-item
              column="r"
              :name="$t('detail.residual.fillet_radii_of_the_cross_section')"
              unit="mm"
            >
              {{ formatNumber(residual, 'r') }}
            </property-item>
            <property-item
              column="A"
              :name="$t('detail.residual.area_of_the_cross_section')"
              unit="mm²"
            >
              {{ formatNumber(residual, 'A') }}
            </property-item>
          </p>
        </v-col>
        <v-col cols="12" sm="6">
          <zoomable-image
            :src="getResidualStressSchematic(residual)"
            :alt="$t('detail.residual.figure_alt')"
          />
        </v-col>
      </v-row>
    </template>
  </common-detail>
</template>
