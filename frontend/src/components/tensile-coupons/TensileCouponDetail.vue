<script setup lang="ts">
import type { TensileCouponModel } from '@/backend'
import CommonDetail, { type DetailCarouselItem } from '@/components/commons/CommonDetail.vue'
import PropertyItem from '@/components/commons/PropertyItem.vue'
import { tensileCouponApi } from '@/plugins/axios'
import { getTensileCouponImage } from '@/utils/component'
import { formatNumber } from '@/utils/formatter'
import type { LineSeriesOption } from 'echarts'
import { computed, ref, watch } from 'vue'

const props = defineProps<{
  tensileCoupon: TensileCouponModel
}>()
const emit = defineEmits<{
  (e: 'close'): void
}>()

const carouselItems = ref<DetailCarouselItem[][]>([])

watch(
  () => props.tensileCoupon,
  (tensileCoupon) => {
    carouselItems.value = [
      [
        {
          count: tensileCoupon.stress_strain_count,
          promise: tensileCouponApi
            .getTensileCouponsStressStrain(tensileCoupon.id)
            .then((response) => response.data.map((serie) => [serie[1], serie[0]]))
            .then((data) => [{ data }] as LineSeriesOption[]),
          title: 'Engineering stress-strain',
          xAxisName: 'ε',
          yAxisName: 'σ [MPa]'
        }
      ]
    ]
  },
  { immediate: true }
)

const profileTypeWithSource = computed(() => {
  const profileType = props.tensileCoupon.profile_type
  const source = props.tensileCoupon.specimen_source
  if (!source || source === 'NA') {
    return profileType
  }
  return `${profileType} (${source})`
})

const publicationLink = computed(() => {
  const link = props.tensileCoupon.link
  if (!link || link === 'TBA') {
    return undefined
  }
  return link
})
</script>

<template>
  <common-detail
    :reference="tensileCoupon.reference ?? ''"
    :link="publicationLink"
    :carousel-items="carouselItems"
    :carousel-height="400"
    @close="emit('close')"
  >
    <template #title>
      {{ tensileCoupon.experimental_program }} ({{ tensileCoupon.year }}) -
      {{ tensileCoupon.id }}
    </template>
    <template #body>
      <v-row>
        <v-col cols="6">
          <div class="mb-5">
            <h2 class="mb-2">Structural Steel Element</h2>
            <p>
              <property-item name="Profile type">
                {{ profileTypeWithSource }}
              </property-item>
              <property-item name="Cross section">
                {{ tensileCoupon.profile }}
              </property-item>
              <property-item name="Reference tensile coupon">
                {{ tensileCoupon.specimen_type }}
              </property-item>
              <property-item name="Temperature" unit="°C">
                {{ tensileCoupon.t_a__deg_c_ }}
              </property-item>
              <property-item name="Standard">
                {{ tensileCoupon.standard }}
              </property-item>
            </p>
          </div>
          <div class="mb-5">
            <h2 class="mb-2">Steel Material Designation</h2>
            <p>
              <property-item name="Steel type">
                {{ tensileCoupon.steel_grade }}
              </property-item>
              <property-item name="Nominal yield stress" unit="MPa">
                {{ formatNumber(tensileCoupon.fy_n__mpa_) }}
              </property-item>
              <property-item name="Measured yield stress" unit="MPa">
                {{ formatNumber(tensileCoupon.yield_stress_02__mpa_, 1) }}
              </property-item>
              <property-item name="Nominal ultimate stress" unit="MPa">
                {{ formatNumber(tensileCoupon.fu_n__mpa_) }}
              </property-item>
              <property-item name="Measured ultimate stress" unit="MPa">
                {{ formatNumber(tensileCoupon.tensile_strength__mpa_, 1) }}
              </property-item>
              <property-item name="Young's modulus, E" unit="MPa">
                {{ formatNumber(tensileCoupon.elastic_modulus__mpa_, 1) }}
              </property-item>
              <property-item name="εy" unit="%">
                {{ formatNumber(tensileCoupon.yield_strain_02, 2) }}
              </property-item>
              <property-item name="εu" unit="%">
                {{ formatNumber(tensileCoupon.elongation_at_fracture, 2) }}
              </property-item>
              <property-item name="εf" unit="%">
                {{ formatNumber(tensileCoupon.elongation_after_fracture, 2) }}
              </property-item>
              <property-item name="Z" unit="%">
                {{ formatNumber(tensileCoupon.reduction_of_area, 2) }}
              </property-item>
            </p>
          </div>
        </v-col>
        <v-col cols="6">
          <v-img :src="getTensileCouponImage()" />
        </v-col>
      </v-row>
    </template>
  </common-detail>
</template>
