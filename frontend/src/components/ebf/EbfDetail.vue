<script setup lang="ts">
import type { EccentricBracedFrameModel } from '@/backend'
import CommonDetail, { type DetailCarouselItem } from '@/components/commons/CommonDetail.vue'
import PropertyItem from '@/components/commons/PropertyItem.vue'
import { ebfApi } from '@/plugins/axios'
import { publicPath } from '@/utils/common'
import { formatNumber } from '@/utils/formatter'
import { computed, ref, watch } from 'vue'

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

// Add more comprehensive mapping for test configurations
const linkConfigs = {
  TF1: 'Isolated link',
  TF2: 'Link in bare frame',
  TF2C: 'Link in composite frame',
  TF3: 'Link in system',
  TF3c: 'Link in system - configuration c'
  // Add other configurations as needed
}

const linkTypeText = {
  short: 'Short',
  intermediate: 'Intermediate',
  long: 'Long'
}

const imageSrc = computed(() => {
  const linkConfiguration = props.eccentricBracedFrame.l_confi
  if (!linkConfiguration) return ''

  const configKey = linkConfiguration.toLowerCase()
  let imageName = ''

  if (configKey === 'tf1') imageName = 'Link_conf1.jpeg'
  else if (configKey === 'tf2') imageName = 'Link_conf2.jpeg'
  else if (configKey === 'tf2c') imageName = 'Link_conf3.jpeg'
  else if (configKey === 'tf3c') imageName = 'Link_conf4.jpeg'
  else return '' // No matching image

  return `${publicPath}img/ebf/link_config/${imageName}`
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
              {{
                linkTypeText[eccentricBracedFrame.class_aisc.toLowerCase()] ||
                eccentricBracedFrame.class_aisc
              }}
            </property-item>
            <property-item name="Link Cross Section">
              {{ eccentricBracedFrame.profile }}
            </property-item>
            <property-item name="Section Type">
              {{ eccentricBracedFrame.sec_type }}
            </property-item>
            <property-item name="Link Length" unit="mm">
              {{ eccentricBracedFrame.e }}
            </property-item>
            <property-item name="Test Setup">
              {{ linkConfigs[eccentricBracedFrame.l_confi] || eccentricBracedFrame.l_confi }}
            </property-item>
          </p>

          <h2 class="mb-2">Steel Material Designation</h2>
          <v-row>
            <v-col cols="6">
              <h3 class="text-subtitle-1">Flange</h3>
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
            <v-col cols="6">
              <h3 class="text-subtitle-1">Web</h3>
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
          <div v-else class="pa-4 text-center">
            <h3>Test Configuration: {{ eccentricBracedFrame.l_confi }}</h3>
            <p class="text-medium-emphasis">
              {{ linkConfigs[eccentricBracedFrame.l_confi] || 'Image not available' }}
            </p>
          </div>
        </v-col>
      </v-row>
    </template>
  </common-detail>
</template>
