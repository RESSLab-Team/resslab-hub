<script setup lang="ts">
import type { MaterialModel } from '@/backend'
import CommonDetail, { type DetailCarouselItem } from '@/components/commons/CommonDetail.vue'
import PropertyItem from '@/components/commons/PropertyItem.vue'
import { materialsApi } from '@/plugins/axios'
import { publicPath } from '@/utils/common'
import { formatNumber } from '@/utils/formatter'
import { computeUvcStress } from '@/utils/material'
import type { LineSeriesOption } from 'echarts'
import { zip } from 'lodash'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })

const props = defineProps<{
  material: MaterialModel
}>()
const emit = defineEmits<{
  (e: 'close'): void
}>()

const carouselItems = ref<DetailCarouselItem[][]>([])

const errorMessage = ref('')

const hasValidUvcParameters = computed(() => {
  return (
    props.material.uvc_e__mpa_ &&
    props.material.uvc_sigma__mpa_ &&
    props.material.uvc_q__mpa_ &&
    props.material.uvc_b &&
    props.material.uvc_d__mpa_ &&
    props.material.uvc_a &&
    props.material.uvc_c1__mpa_ &&
    props.material.uvc_g1 &&
    props.material.uvc_c2__mpa_ &&
    props.material.uvc_g2
  )
})

const showGraph = computed(() => {
  return hasValidUvcParameters.value && carouselItems.value.length > 0
})

watch(
  () => props.material,
  (material) => {
    if (!hasValidUvcParameters.value) {
      errorMessage.value = t('detail.material.error_message')
      return
    } else {
      errorMessage.value = ''
      carouselItems.value = [
        [
          {
            count: material.stress_strain_count,
            promise: materialsApi
              .getMaterialsStressStrain(material.id)
              .then((response) => response.data)
              .then((series) => {
                const stressStrain = series.map((serie) => [serie[1], serie[0]])
                const strain = series.map((serie) => serie[1])
                const uvcStress = computeUvcStress(
                  strain,
                  material.uvc_e__mpa_! * 1000,
                  material.uvc_sigma__mpa_!,
                  material.uvc_q__mpa_!,
                  material.uvc_b!,
                  material.uvc_d__mpa_!,
                  material.uvc_a!,
                  [
                    {
                      c: material.uvc_c1__mpa_!,
                      gamma: material.uvc_g1!
                    },
                    {
                      c: material.uvc_c2__mpa_!,
                      gamma: material.uvc_g2!
                    }
                  ]
                )
                const uvc = zip(strain, uvcStress).filter(
                  (v): v is [number, number] => v[0] !== undefined && v[1] !== undefined
                )
                return [
                  {
                    name: t('detail.material.test_data'),
                    data: stressStrain
                  },
                  {
                    name: t('detail.material.simulation'),
                    data: uvc
                  }
                ] as LineSeriesOption[]
              }),
            title: t('detail.material.true_stress_strain'),
            xAxisName: 'ε',
            yAxisName: 'σ [MPa]'
          }
        ]
      ]
    }
  },
  {
    immediate: true
  }
)
</script>

<template>
  <common-detail
    database-id="cyclic"
    :record="material"
    :reference="material.reference ?? ''"
    :link="material.link ?? ''"
    :carousel-items="showGraph ? carouselItems : []"
    :carousel-height="400"
    @close="emit('close')"
  >
    <template #title>
      {{ material.experimental_program }} ({{ material.date }}) -
      {{ material.id }}
    </template>
    <template #body>
      <v-alert v-if="errorMessage" class="my-10" variant="outlined" type="warning">{{
        errorMessage
      }}</v-alert>

      <v-row>
        <v-col cols="6">
          <div class="mb-5">
            <h2 class="mb-2">{{ $t('detail.material.structural_steel_element') }}</h2>
            <p>
              <property-item :name="$t('detail.material.profile_type')">
                {{ material.profile_type }}
              </property-item>
              <property-item :name="$t('detail.material.cross_section')">
                {{ material.profile }} {{ material.source }}
              </property-item>
              <property-item :name="$t('detail.material.reference_round_coupon')">
                {{ material.size }}
              </property-item>
              <property-item :name="$t('detail.material.temperature')" unit="°C">
                {{ material.t_a__deg_c_ }}
              </property-item>
            </p>
          </div>
          <div class="mb-5">
            <h2 class="mb-2">{{ $t('detail.material.steel_material_designation') }}</h2>
            <p>
              <property-item :name="$t('detail.material.steel_type')">
                {{ material.grade }} {{ material.spec }}
              </property-item>
              <property-item :name="$t('detail.material.nominal_yield_stress')" unit="MPa">
                {{ formatNumber(material.fy_n__mpa_) }}
              </property-item>
              <property-item :name="$t('detail.material.measured_yield_stress')" unit="MPa">
                {{ formatNumber(material.yield_stress__mpa_, 1) }}
              </property-item>
              <property-item :name="$t('detail.material.nominal_ultimate_stress')" unit="MPa">
                {{ formatNumber(material.fu_n__mpa_) }}
              </property-item>
            </p>
          </div>
          <div class="mb-5">
            <h2 class="mb-2">{{ $t('detail.material.material_model_parameters') }}</h2>
            <p>
              <property-item :name="$t('detail.material.youngs_modulus')" unit="MPa">
                {{ formatNumber((material.uvc_e__mpa_ ?? 0) * 1000, 1) }}
              </property-item>
              <property-item :name="$t('detail.material.initial_yield_stress')" unit="MPa">
                {{ formatNumber(material.uvc_sigma__mpa_, 1) }}
              </property-item>
              <property-item :name="$t('detail.material.isotropic_hardening_magnitude')" unit="MPa">
                {{ formatNumber(material.uvc_q__mpa_, 1) }}
              </property-item>
              <property-item :name="$t('detail.material.isotropic_hardening_rate')">
                {{ formatNumber(material.uvc_b, 1) }}
              </property-item>
              <property-item :name="$t('detail.material.discount_yielding_parameter')" unit="MPa">
                {{ formatNumber(material.uvc_d__mpa_, 1) }}
              </property-item>
              <property-item :name="$t('detail.material.discount_yielding_rate')">
                {{ formatNumber(material.uvc_a, 1) }}
              </property-item>
              <property-item :name="$t('detail.material.backstress_magnitude_1')" unit="MPa">
                {{ formatNumber(material.uvc_c1__mpa_, 1) }}
              </property-item>
              <property-item :name="$t('detail.material.backstress_magnitude_2')" unit="MPa">
                {{ formatNumber(material.uvc_c2__mpa_, 1) }}
              </property-item>
              <property-item :name="$t('detail.material.backstress_rate_1')">
                {{ formatNumber(material.uvc_g1, 1) }}
              </property-item>
              <property-item :name="$t('detail.material.backstress_rate_2')">
                {{ formatNumber(material.uvc_g2, 1) }}
              </property-item>
            </p>
          </div>
        </v-col>
        <v-col cols="6">
          <v-img :src="publicPath + 'img/material/detail.png'" />
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          {{ $t('detail.material.model_footnote') }}
          <a
            href="https://ascelibrary.org/doi/abs/10.1061/%28ASCE%29ST.1943-541X.0002964"
            target="_blank"
          >
            Hartloper et al. (2021)
          </a>
        </v-col>
      </v-row>
    </template>
  </common-detail>
</template>
