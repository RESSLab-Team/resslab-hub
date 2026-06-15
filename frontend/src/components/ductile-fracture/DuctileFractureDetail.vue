<script setup lang="ts">
import type { DuctileFractureModel } from '@/backend'
import CommonDetail from '@/components/commons/CommonDetail.vue'
import PropertyItem from '@/components/commons/PropertyItem.vue'
import DuctileFracturePlotSlot from '@/components/ductile-fracture/charts/DuctileFracturePlotSlot.vue'
import SemDialog from '@/components/ductile-fracture/sem/SemDialog.vue'
import { getDuctileFractureImage } from '@/utils/component'
import type { DuctileFracturePlotId } from '@/utils/ductile_fracture'
import { formatNumber } from '@/utils/formatter'
import { mdiMagnifyPlusOutline } from '@mdi/js'
import { computed, ref } from 'vue'

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

const semOpen = ref(false)
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
            <h2 class="mb-2">{{ $t('detail.ductile_fracture.structural_steel_element') }}</h2>
            <p>
              <property-item :name="$t('detail.ductile_fracture.coupon_location')">
                {{ ductileFracture.location_coupon }}
              </property-item>
              <property-item :name="$t('detail.ductile_fracture.section_profile')">
                {{ ductileFracture.section_profile }}
              </property-item>
              <property-item :name="$t('detail.ductile_fracture.plate_thickness')" unit="mm">
                {{ formatNumber(ductileFracture.plate_thickness) }}
              </property-item>
              <property-item :name="$t('detail.ductile_fracture.temperature')" unit="°C">
                {{ formatNumber(ductileFracture.temperature) }}
              </property-item>
            </p>
          </div>
          <div class="mb-5">
            <h2 class="mb-2">{{ $t('detail.ductile_fracture.steel_material_designation') }}</h2>
            <p>
              <property-item :name="$t('detail.ductile_fracture.steel_type')">
                {{ ductileFracture.steel_type }}
              </property-item>
              <property-item :name="$t('detail.ductile_fracture.nominal_yield_stress')" unit="MPa">
                {{ formatNumber(ductileFracture.f_yn) }}
              </property-item>
              <property-item :name="$t('detail.ductile_fracture.measured_yield_stress')" unit="MPa">
                {{ formatNumber(ductileFracture.fy_m) }}
              </property-item>
              <property-item
                :name="$t('detail.ductile_fracture.nominal_ultimate_stress')"
                unit="MPa"
              >
                {{ formatNumber(ductileFracture.f_un) }}
              </property-item>
              <property-item
                :name="$t('detail.ductile_fracture.measured_ultimate_stress')"
                unit="MPa"
              >
                {{ formatNumber(ductileFracture.fu_m) }}
              </property-item>
            </p>
          </div>
          <div class="mb-5">
            <h2 class="mb-2">{{ $t('detail.ductile_fracture.fracture_model_parameters') }}</h2>
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
              <property-item :name="$t('detail.ductile_fracture.characteristic_length')" unit="mm">
                {{ formatNumber(ductileFracture.l_star, 3) }}
              </property-item>
            </p>
          </div>
        </v-col>
        <v-col cols="6">
          <v-img :src="getDuctileFractureImage()" />
        </v-col>
      </v-row>
      <v-row v-if="ductileFracture.has_sem">
        <v-col cols="12">
          <v-btn block size="large" :prepend-icon="mdiMagnifyPlusOutline" @click="semOpen = true">
            {{ $t('detail.ductile_fracture.sem_button') }}
          </v-btn>
        </v-col>
      </v-row>
      <sem-dialog v-model="semOpen" :model="ductileFracture" />
    </template>
  </common-detail>
</template>
