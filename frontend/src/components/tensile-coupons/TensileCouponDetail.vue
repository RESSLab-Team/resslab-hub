<script setup lang="ts">
import type { TensileCouponModel } from '@/backend'
import CommonDetail, { type DetailCarouselItem } from '@/components/commons/CommonDetail.vue'
import PropertyItem from '@/components/commons/PropertyItem.vue'
import { tensileCouponApi } from '@/plugins/axios'
import { isHttpUrl } from '@/utils/common'
import { getTensileCouponImage } from '@/utils/component'
import { formatNumber } from '@/utils/formatter'
import type { LineSeriesOption } from 'echarts'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })

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
          title: t('detail.tensile_coupon.engineering_stress_strain'),
          xAxisName: 'ε',
          yAxisName: 'σ [MPa]',
          xAxisMin: 0,
          yAxisMin: 0
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
  return isHttpUrl(link) ? link : undefined
})
</script>

<template>
  <common-detail
    database-id="tensile"
    :record="tensileCoupon"
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
        <v-col cols="12" sm="6">
          <div class="mb-5">
            <h2 class="mb-2">{{ $t('detail.tensile_coupon.structural_steel_element') }}</h2>
            <p>
              <property-item :name="$t('detail.tensile_coupon.profile_type')">
                {{ profileTypeWithSource }}
              </property-item>
              <property-item :name="$t('detail.tensile_coupon.cross_section')">
                {{ tensileCoupon.profile }}
              </property-item>
              <property-item :name="$t('detail.tensile_coupon.reference_tensile_coupon')">
                {{ tensileCoupon.specimen_type }}
              </property-item>
              <property-item :name="$t('detail.tensile_coupon.temperature')" unit="°C">
                {{ tensileCoupon.t_a__deg_c_ }}
              </property-item>
              <property-item :name="$t('detail.tensile_coupon.standard')">
                {{ tensileCoupon.standard }}
              </property-item>
            </p>
          </div>
          <div class="mb-5">
            <h2 class="mb-2">{{ $t('detail.tensile_coupon.steel_material_designation') }}</h2>
            <p>
              <property-item :name="$t('detail.tensile_coupon.steel_type')">
                {{ tensileCoupon.steel_grade }}
              </property-item>
              <property-item :name="$t('detail.tensile_coupon.nominal_yield_stress')" unit="MPa">
                {{ formatNumber(tensileCoupon.fy_n__mpa_) }}
              </property-item>
              <property-item :name="$t('detail.tensile_coupon.measured_yield_stress')" unit="MPa">
                {{ formatNumber(tensileCoupon.yield_stress_02__mpa_, 1) }}
              </property-item>
              <property-item :name="$t('detail.tensile_coupon.nominal_ultimate_stress')" unit="MPa">
                {{ formatNumber(tensileCoupon.fu_n__mpa_) }}
              </property-item>
              <property-item
                :name="$t('detail.tensile_coupon.measured_ultimate_stress')"
                unit="MPa"
              >
                {{ formatNumber(tensileCoupon.tensile_strength__mpa_, 1) }}
              </property-item>
              <property-item :name="$t('detail.tensile_coupon.youngs_modulus_e')" unit="MPa">
                {{ formatNumber(tensileCoupon.elastic_modulus__mpa_, 1) }}
              </property-item>
              <property-item name="εy">
                {{ formatNumber(tensileCoupon.yield_strain_02, 5) }}
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
        <v-col cols="12" sm="6">
          <v-img :src="getTensileCouponImage()" />
        </v-col>
      </v-row>
    </template>
  </common-detail>
</template>
