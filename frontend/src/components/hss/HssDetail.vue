<script setup lang="ts">
import type { HSSColumnModel } from '@/backend'
import CommonDetail, { type DetailCarouselItem } from '@/components/commons/CommonDetail.vue'
import PropertyItem from '@/components/commons/PropertyItem.vue'
import { hssApi } from '@/plugins/axios'
import { getHSSColumnImage } from '@/utils/component'
import { formatNumber } from '@/utils/formatter'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps<{
  hssColumn: HSSColumnModel
}>()
const emit = defineEmits<{
  (e: 'close'): void
}>()

const carouselItems = ref<DetailCarouselItem[][]>([])

watch(
  () => props.hssColumn,
  (hssColumn) => {
    carouselItems.value = [
      [
        {
          count: hssColumn.moment_rotation_count,
          promise: hssApi.getHssColumnsMomentRotation(hssColumn.id),
          title: t('detail.hss.moment_rotation_title'),
          xAxisName: t('detail.hss.chord_rotation_axis'),
          yAxisName: t('detail.hss.moment_axis')
        }
      ]
    ]
  },
  {
    immediate: true
  }
)

const testConfigurationImageSrc = computed<string>(() =>
  getHSSColumnImage(props.hssColumn.test_configuration)
)
</script>

<template>
  <common-detail
    :reference="hssColumn.reference"
    :link="hssColumn.url"
    :carousel-items="carouselItems"
    @close="emit('close')"
  >
    <template #title>
      {{ hssColumn.id.replaceAll('_', ' ') }}
    </template>
    <template #body>
      <v-row>
        <v-col class="mt-6" cols="6">
          <h2 class="mb-2">{{ $t('detail.hss.loading_geometric_parameters') }}</h2>
          <p class="mb-6">
            <property-item :name="$t('detail.hss.loading_protocol')">
              {{ hssColumn.loading_protocol }}
            </property-item>
            <property-item :name="$t('detail.hss.axial_load_ratio')">
              {{ hssColumn.axial_load_sequence }}
            </property-item>
            <property-item name="Pg/Py">
              {{ hssColumn.axial_load_ratio }}
            </property-item>
            <property-item :name="$t('detail.hss.test_configuration')">
              {{ hssColumn.test_configuration }}
            </property-item>
            <property-item :name="$t('detail.hss.column_cross_section')">
              {{ hssColumn.tube_section }}
            </property-item>
            <property-item :name="$t('detail.hss.member_length')" unit="mm">
              {{ hssColumn.length__mm }}
            </property-item>
          </p>
          <h2 class="mb-2">{{ $t('detail.hss.steel_material_designation') }}</h2>
          <p class="mb-6">
            <property-item :name="$t('detail.hss.steel_type')">
              {{ hssColumn.steel_type }}
            </property-item>
            <property-item :name="$t('detail.hss.nominal_yield_stress')" unit="MPa">
              {{ formatNumber(hssColumn.fy_nominal__n_mm2) }}
            </property-item>
            <property-item :name="$t('detail.hss.measured_yield_stress')" unit="MPa">
              {{ formatNumber(hssColumn.fy_measured__n_mm2) }}
            </property-item>
            <property-item :name="$t('detail.hss.measured_ultimate_stress')" unit="MPa">
              {{ formatNumber(hssColumn.f_ultimate__n_mm2) }}
            </property-item>
          </p>
        </v-col>
        <v-col cols="6">
          <v-img :src="testConfigurationImageSrc" />
        </v-col>
      </v-row>
    </template>
  </common-detail>
</template>
