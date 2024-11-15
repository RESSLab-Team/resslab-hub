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
    console.log(hasValidUvcParameters.value, props.material.uvc_q__mpa_)
    if (!hasValidUvcParameters.value) {
      errorMessage.value = 'Material model UVC parameters are missing so graph is not available.'
      return
    } else {
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
                    name: 'Test Data',
                    data: stressStrain
                  },
                  {
                    name: 'Simulation',
                    data: uvc
                  }
                ] as LineSeriesOption[]
              }),
            title: 'True Stress Strain',
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
          <h2>Structural Steel Element</h2>
          <p>
            <property-item name="Profile type">
              {{ material.profile_type }}
            </property-item>
            <property-item name="Cross section">
              {{ material.profile }} {{ material.source }}
            </property-item>
            <property-item name="Reference round coupon">
              {{ material.size }}
            </property-item>
            <property-item name="Temperature" unit="°C">
              {{ material.t_a__deg_c_ }}
            </property-item>
          </p>
          <h2>Steel Material Designation</h2>
          <p>
            <property-item name="Steel type">
              {{ material.grade }} {{ material.spec }}
            </property-item>
            <property-item name="Nominal yield stress" unit="MPa">
              {{ formatNumber(material.fy_n__mpa_) }}
            </property-item>
            <property-item name="Measured yield stress" unit="MPa">
              {{ formatNumber(material.yield_stress__mpa_, 1) }}
            </property-item>
            <property-item name="Nominal ultimate stress" unit="MPa">
              {{ formatNumber(material.fu_n__mpa_) }}
            </property-item>
          </p>
          <h2>Material Model Parameters *</h2>
          <p>
            <property-item name="Young's modulus, E" unit="MPa">
              {{ formatNumber((material.uvc_e__mpa_ ?? 0) * 1000, 1) }}
            </property-item>
            <property-item name="Initial yield stress, σyo" unit="MPa">
              {{ formatNumber(material.uvc_sigma__mpa_, 1) }}
            </property-item>
            <property-item name="Parameter for magnitude of isotropic hardening, Q" unit="MPa">
              {{ formatNumber(material.uvc_q__mpa_, 1) }}
            </property-item>
            <property-item name="Rate of isotropic hardening, b">
              {{ formatNumber(material.uvc_b, 1) }}
            </property-item>
            <property-item name="Parameter for discount yielding, D" unit="MPa">
              {{ formatNumber(material.uvc_d__mpa_, 1) }}
            </property-item>
            <property-item name="Rate of decrease for discount yielding, a">
              {{ formatNumber(material.uvc_a, 1) }}
            </property-item>
            <property-item name="Magnitude of backstress 1, C1" unit="MPa">
              {{ formatNumber(material.uvc_c1__mpa_, 1) }}
            </property-item>
            <property-item name="Magnitude of backstress 2, C2" unit="MPa">
              {{ formatNumber(material.uvc_c2__mpa_, 1) }}
            </property-item>
            <property-item name="Rate of backstress 1, γ1">
              {{ formatNumber(material.uvc_g1, 1) }}
            </property-item>
            <property-item name="Rate of backstress 2, γ2">
              {{ formatNumber(material.uvc_g2, 1) }}
            </property-item>
          </p>
        </v-col>
        <v-col cols="6">
          <v-img :src="publicPath + 'img/material/detail.png'" />
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          * The material model is based on
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
