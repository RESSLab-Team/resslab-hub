<script setup lang="ts">
import type { DuctileFractureModel } from '@/backend'
import CommonDetail from '@/components/commons/CommonDetail.vue'
import PropertyItem from '@/components/commons/PropertyItem.vue'
import DuctileFracturePlotSlot from '@/components/ductile-fracture/charts/DuctileFracturePlotSlot.vue'
import { getDuctileFractureImage } from '@/utils/component'
import type { DuctileFracturePlotId } from '@/utils/ductile_fracture'
import { formatNumber } from '@/utils/formatter'
import { computed } from 'vue'

const props = defineProps<{
  ductileFracture: DuctileFractureModel
}>()
const emit = defineEmits<{
  (e: 'close'): void
}>()

const publicationLink = computed(() => {
  const link = props.ductileFracture.link
  if (!link || link === 'TBA') {
    return undefined
  }
  return link
})

const leftOptions = computed<DuctileFracturePlotId[]>(() => {
  const opts: DuctileFracturePlotId[] = []
  if (props.ductileFracture.force_elongation_count > 0) opts.push('force-axial')
  if (props.ductileFracture.force_radial_count > 0) opts.push('force-radial')
  return opts
})
const rightOptions = computed<DuctileFracturePlotId[]>(() => {
  const opts: DuctileFracturePlotId[] = []
  if (props.ductileFracture.triax_simulation_count > 0) opts.push('triax')
  if (props.ductileFracture.lode_simulation_count > 0) opts.push('lode')
  if (props.ductileFracture.epeq_simulation_count > 0) opts.push('epeq')
  return opts
})
const twoFigures = computed(() => rightOptions.value.length > 0)
const showPlots = computed(() => leftOptions.value.length > 0 || twoFigures.value)
</script>

<template>
  <common-detail
    :reference="ductileFracture.reference ?? ''"
    :link="publicationLink"
    :carousel-items="[]"
    :carousel-height="400"
    @close="emit('close')"
  >
    <template #title>
      {{ ductileFracture.experimental_program }} ({{ ductileFracture.date }}) -
      {{ ductileFracture.specimen_designation }}
    </template>
    <template #body>
      <v-row v-if="showPlots" class="mt-2 mb-2">
        <v-col :cols="twoFigures ? 6 : 12">
          <ductile-fracture-plot-slot
            v-if="leftOptions.length > 0"
            :model="ductileFracture"
            :options="leftOptions"
            :default-plot="leftOptions[0]"
          />
        </v-col>
        <v-col v-if="twoFigures" cols="6">
          <ductile-fracture-plot-slot
            :model="ductileFracture"
            :options="rightOptions"
            :default-plot="rightOptions[0]"
          />
        </v-col>
      </v-row>
      <v-row>
        <v-col cols="6">
          <div class="mb-5">
            <h2 class="mb-2">Structural Steel Element</h2>
            <p>
              <property-item name="Coupon location">
                {{ ductileFracture.location_coupon }}
              </property-item>
              <property-item name="Section profile">
                {{ ductileFracture.section_profile }}
              </property-item>
              <property-item name="Plate thickness" unit="mm">
                {{ formatNumber(ductileFracture.plate_thickness) }}
              </property-item>
              <property-item name="Temperature" unit="°C">
                {{ formatNumber(ductileFracture.temperature) }}
              </property-item>
            </p>
          </div>
          <div class="mb-5">
            <h2 class="mb-2">Steel Material Designation</h2>
            <p>
              <property-item name="Steel type">
                {{ ductileFracture.steel_type }}
              </property-item>
              <property-item name="Nominal yield stress" unit="MPa">
                {{ formatNumber(ductileFracture.f_yn) }}
              </property-item>
              <property-item name="Measured yield stress" unit="MPa">
                {{ formatNumber(ductileFracture.fy_m) }}
              </property-item>
              <property-item name="Nominal ultimate stress" unit="MPa">
                {{ formatNumber(ductileFracture.f_un) }}
              </property-item>
              <property-item name="Measured ultimate stress" unit="MPa">
                {{ formatNumber(ductileFracture.fu_m) }}
              </property-item>
            </p>
          </div>
          <div class="mb-5">
            <h2 class="mb-2">Fracture Model Parameters</h2>
            <p>
              <property-item name="SWDFM C">
                {{ formatNumber(ductileFracture.swdfm_C, 3) }}
              </property-item>
              <property-item name="SWDFM κ">
                {{ formatNumber(ductileFracture.swdfm_kappa, 3) }}
              </property-item>
              <property-item name="SWDFM β">
                {{ formatNumber(ductileFracture.swdfm_beta, 3) }}
              </property-item>
              <property-item name="CVGM η">
                {{ formatNumber(ductileFracture.cvgm_etamono, 3) }}
              </property-item>
              <property-item name="CVGM λ">
                {{ formatNumber(ductileFracture.cvgm_lambda, 3) }}
              </property-item>
              <property-item name="Characteristic length" unit="mm">
                {{ formatNumber(ductileFracture.l_star, 3) }}
              </property-item>
            </p>
          </div>
        </v-col>
        <v-col cols="6">
          <v-img :src="getDuctileFractureImage()" />
        </v-col>
      </v-row>
    </template>
  </common-detail>
</template>
