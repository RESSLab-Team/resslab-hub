<script setup lang="ts">
import type { EccentricBracedFrameModel } from '@/backend'
import CommonDetail, { type DetailCarouselItem } from '@/components/commons/CommonDetail.vue'
import PropertyItem from '@/components/commons/PropertyItem.vue'
import { ebfApi } from '@/plugins/axios'
import { formatNumber } from '@/utils/formatter'
import { computed, ref, watch } from 'vue'
import { linkConfigurationMapping } from '@/utils/ebf'
import { getEbfImage } from '@/utils/component'

const props = defineProps<{
  eccentricBracedFrame: EccentricBracedFrameModel
}>()
const emit = defineEmits<{
  (e: 'close'): void
}>()

const carouselItems = ref<DetailCarouselItem[][]>([])

watch(
  () => props.eccentricBracedFrame,
  (ebf) => {
    carouselItems.value = [
      [
        {
          count: ebf.shear_link_angle_count,
          promise: ebfApi.getEccentricBracedFramesShearLinkAngle(ebf.id),
          title: '', // No title as specified
          xAxisName: 'Link Rotation [rad]',
          yAxisName: 'Link Shear [kN]'
        }
      ]
    ]
  },
  {
    immediate: true
  }
)

const imageSrc = computed(() => {
  const linkConfiguration = props.eccentricBracedFrame.l_confi
  if (!linkConfiguration) return ''

  const configKey = linkConfiguration

  return getEbfImage(configKey)
})
</script>

<template>
  <common-detail
    :reference="eccentricBracedFrame.reference"
    :link="eccentricBracedFrame.url"
    :carousel-items="carouselItems"
    @close="emit('close')"
  >
    <template #title>
      {{ eccentricBracedFrame.investigator }} ({{ eccentricBracedFrame.year }}) -
      {{ eccentricBracedFrame.spec_id }}
    </template>
    <template #body>
      <v-row>
        <v-col class="mt-6" cols="6">
          <h2 class="mb-2">Loading and Geometric Parameters</h2>
          <p class="mb-6">
            <property-item name="Loading Protocol">
              {{ eccentricBracedFrame.l_p_typ }}
            </property-item>
            <property-item name="Link Location">
              {{ eccentricBracedFrame.link_loc }}
            </property-item>
            <property-item name="Link Type">
              {{ eccentricBracedFrame.class_aisc }}
            </property-item>
            <property-item name="Link Cross Section">
              {{ eccentricBracedFrame.profile }}
            </property-item>
            <property-item name="Section Type">
              {{ eccentricBracedFrame.sec_type }}
            </property-item>
            <property-item name="Link Length, e" unit="mm">
              {{ eccentricBracedFrame.e }}
            </property-item>
            <property-item name="Test Setup">
              {{
                eccentricBracedFrame.l_confi
                  ? linkConfigurationMapping.get(eccentricBracedFrame.l_confi)
                  : 'Not defined'
              }}
            </property-item>
            <property-item name="Link Connection Type">
              {{ eccentricBracedFrame.l_con_typ }}
            </property-item>
          </p>

          <h2 class="mb-2">Steel Material Designation</h2>
          <v-row>
            <v-col cols="12">
              <h3>Flange</h3>
              <property-item name="Steel Type">
                {{ eccentricBracedFrame.sg_flg_link }}
              </property-item>
              <property-item name="Nominal Yield Stress" unit="MPa">
                {{ formatNumber(eccentricBracedFrame.f_y_n_flg) }}
              </property-item>
              <property-item name="Measured Yield Stress" unit="MPa">
                {{ formatNumber(eccentricBracedFrame.f_y_m_flg) }}
              </property-item>
              <property-item name="Measured Ultimate Stress" unit="MPa">
                {{ formatNumber(eccentricBracedFrame.f_u_m_flg) }}
              </property-item>
            </v-col>
            <v-col cols="12">
              <h3>Web</h3>
              <property-item name="Steel Type">
                {{ eccentricBracedFrame.sg_web_link }}
              </property-item>
              <property-item name="Nominal Yield Stress" unit="MPa">
                {{ formatNumber(eccentricBracedFrame.f_y_n_web) }}
              </property-item>
              <property-item name="Measured Yield Stress" unit="MPa">
                {{ formatNumber(eccentricBracedFrame.f_y_m_web) }}
              </property-item>
              <property-item name="Measured Ultimate Stress" unit="MPa">
                {{ formatNumber(eccentricBracedFrame.f_u_m_web) }}
              </property-item>
            </v-col>
          </v-row>
        </v-col>
        <v-col cols="6">
          <v-img v-if="imageSrc" :src="imageSrc" max-height="400" contain />
        </v-col>
      </v-row>
    </template>
  </common-detail>
</template>
