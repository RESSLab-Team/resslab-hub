<script setup lang="ts">
import type { ResidualStressModel } from '@/backend'
import CommonDetail, { type DetailCarouselItem } from '@/components/commons/CommonDetail.vue'
import PropertyItem from '@/components/commons/PropertyItem.vue'
import { publicPath } from '@/utils/common'
import { formatNumber } from '@/utils/formatter'
import { ref, watch } from 'vue'

const props = defineProps<{
  residual: ResidualStressModel
}>()
const emit = defineEmits<{
  (e: 'close'): void
}>()

const carouselItems = ref<DetailCarouselItem[][]>([])

watch(
  () => props.residual,
  (residual) => {
    carouselItems.value = [[]]
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
        <v-col cols="6">
          <h2>Structural Steel Element</h2>
          <p>
            <property-item name="Profile type">
              {{ residual.profile_type }}
            </property-item>
            <property-item name="Cross section">
              {{ residual.profile }}
            </property-item>
          </p>
          <h2>Steel Material Designation</h2>
          <p>
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
          <h2>Cross-Sectional Geometric Properties</h2>
          <p>
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
      <v-row>
        <v-col>
          TODO * The residual model is based on
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
