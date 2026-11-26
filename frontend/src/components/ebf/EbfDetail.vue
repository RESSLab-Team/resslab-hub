<script setup lang="ts">
import type { EccentricBracedFrameModel } from '@/backend'
import CommonDetail, { type DetailCarouselItem } from '@/components/commons/CommonDetail.vue'
import PropertyItem from '@/components/commons/PropertyItem.vue'
import ZoomableImage from '@/components/commons/ZoomableImage.vue'
import { ebfApi } from '@/plugins/axios'
import { useRecordFormat } from '@/composables/useRecordFormat'
import { computed, ref, watch } from 'vue'
import { linkConfigurationMapping } from '@/utils/ebf'
import { getEbfImage } from '@/utils/component'
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })

const props = defineProps<{
  eccentricBracedFrame: EccentricBracedFrameModel
}>()

const formatNumber = useRecordFormat('ebf')
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
          xAxisName: t('detail.ebf.link_rotation_axis'),
          yAxisName: t('detail.ebf.link_shear_axis')
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
    database-id="ebf"
    :record="eccentricBracedFrame"
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
        <v-col class="mt-6" cols="12" sm="6">
          <h2 class="mb-2">{{ $t('detail.ebf.loading_geometric_parameters') }}</h2>
          <p class="mb-6">
            <property-item column="l_p_typ" :name="$t('detail.ebf.loading_protocol')">
              {{ eccentricBracedFrame.l_p_typ }}
            </property-item>
            <property-item column="link_loc" :name="$t('detail.ebf.link_location')">
              {{ eccentricBracedFrame.link_loc }}
            </property-item>
            <property-item column="class_aisc" :name="$t('detail.ebf.link_type')">
              {{ eccentricBracedFrame.class_aisc }}
            </property-item>
            <property-item column="profile" :name="$t('detail.ebf.link_cross_section')">
              {{ eccentricBracedFrame.profile }}
            </property-item>
            <property-item column="sec_type" :name="$t('detail.ebf.section_type')">
              {{ eccentricBracedFrame.sec_type }}
            </property-item>
            <property-item column="e" :name="$t('detail.ebf.link_length')" unit="mm">
              {{ eccentricBracedFrame.e }}
            </property-item>
            <property-item column="l_confi" :name="$t('detail.ebf.test_setup')">
              {{
                eccentricBracedFrame.l_confi
                  ? linkConfigurationMapping().get(eccentricBracedFrame.l_confi)
                  : 'Not defined'
              }}
            </property-item>
            <property-item column="l_con_typ" :name="$t('detail.ebf.link_connection_type')">
              {{ eccentricBracedFrame.l_con_typ }}
            </property-item>
          </p>

          <h2 class="mb-2">{{ $t('detail.ebf.steel_material_designation') }}</h2>
          <v-row>
            <v-col cols="12">
              <h3>{{ $t('detail.ebf.flange') }}</h3>
              <property-item column="sg_flg_link" :name="$t('detail.ebf.steel_type')">
                {{ eccentricBracedFrame.sg_flg_link }}
              </property-item>
              <property-item
                column="f_y_n_flg"
                :name="$t('detail.ebf.nominal_yield_stress')"
                unit="MPa"
              >
                {{ formatNumber(eccentricBracedFrame, 'f_y_n_flg') }}
              </property-item>
              <property-item
                column="f_y_m_flg"
                :name="$t('detail.ebf.measured_yield_stress')"
                unit="MPa"
              >
                {{ formatNumber(eccentricBracedFrame, 'f_y_m_flg') }}
              </property-item>
              <property-item
                column="f_u_m_flg"
                :name="$t('detail.ebf.measured_ultimate_stress')"
                unit="MPa"
              >
                {{ formatNumber(eccentricBracedFrame, 'f_u_m_flg') }}
              </property-item>
            </v-col>
            <v-col cols="12">
              <h3>{{ $t('detail.ebf.web') }}</h3>
              <property-item column="sg_web_link" :name="$t('detail.ebf.steel_type')">
                {{ eccentricBracedFrame.sg_web_link }}
              </property-item>
              <property-item
                column="f_y_n_web"
                :name="$t('detail.ebf.nominal_yield_stress')"
                unit="MPa"
              >
                {{ formatNumber(eccentricBracedFrame, 'f_y_n_web') }}
              </property-item>
              <property-item
                column="f_y_m_web"
                :name="$t('detail.ebf.measured_yield_stress')"
                unit="MPa"
              >
                {{ formatNumber(eccentricBracedFrame, 'f_y_m_web') }}
              </property-item>
              <property-item
                column="f_u_m_web"
                :name="$t('detail.ebf.measured_ultimate_stress')"
                unit="MPa"
              >
                {{ formatNumber(eccentricBracedFrame, 'f_u_m_web') }}
              </property-item>
            </v-col>
          </v-row>
        </v-col>
        <v-col cols="12" sm="6">
          <zoomable-image
            v-if="imageSrc"
            :src="imageSrc"
            :alt="$t('detail.ebf.figure_alt')"
            :max-height="400"
          />
        </v-col>
      </v-row>
    </template>
  </common-detail>
</template>
