<script setup lang="ts">
import type { HSSColumnModel } from '@/backend'
import CommonDetail, { type DetailCarouselItem } from '@/components/commons/CommonDetail.vue'
import PropertyItem from '@/components/commons/PropertyItem.vue'
import { hssApi } from '@/plugins/axios'
import { publicPath } from '@/utils/common'
import { formatNumber } from '@/utils/formatter'
import { ref, watch } from 'vue'

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
          title: 'Moment Rotation',
          xAxisName: 'Chord Rotation [rads]',
          yAxisName: 'Moment [kN.mm]'
        }
      ]
    ]
  },
  {
    immediate: true
  }
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
          <h2 class="mb-2">Loading and Gemotric Parameters</h2>
          <p class="mb-6">
            <property-item name="Loading Protocol">
              {{ hssColumn.loading_protocol }}
            </property-item>
            <property-item name="Axial load ratio">
              {{ hssColumn.axial_load_sequence }}
            </property-item>
            <property-item name="Pg/Py">
              {{ hssColumn.axial_load_ratio }}
            </property-item>
            <property-item name="Boundary conditions">
              {{ hssColumn.test_configuration }}
            </property-item>
            <property-item name="Column cross section">
              {{ hssColumn.tube_section }}
            </property-item>
            <property-item name="Member length" unit="mm">
              {{ hssColumn.length__mm }}
            </property-item>
          </p>
          <h2 class="mb-2">Steel Material Designation</h2>
          <p class="mb-6">
            <property-item name="Steel type">
              {{ hssColumn.steel_type }}
            </property-item>
            <property-item name="Nominal yield stress" unit="MPa">
              {{ formatNumber(hssColumn.fy_nominal__n_mm2) }}
            </property-item>
            <property-item name="Measured yield stress" unit="MPa">
              {{ formatNumber(hssColumn.fy_measured__n_mm2) }}
            </property-item>
            <property-item name="Measured ultimate stress" unit="MPa">
              {{ formatNumber(hssColumn.f_ultimate__n_mm2) }}
            </property-item>
          </p>
        </v-col>
        <v-col cols="6">
          <v-img :src="publicPath + 'img/hssColumns/detail.png'" />
        </v-col>
      </v-row>
    </template>
  </common-detail>
</template>
