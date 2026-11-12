<script setup lang="ts">
import type { DuctileFractureModel } from '@/backend'
import CommonDetail from '@/components/commons/CommonDetail.vue'
import PropertyItem from '@/components/commons/PropertyItem.vue'
import ZoomableImage from '@/components/commons/ZoomableImage.vue'
import DuctileFracturePlotSlot from '@/components/ductile-fracture/charts/DuctileFracturePlotSlot.vue'
import SemDialog from '@/components/ductile-fracture/sem/SemDialog.vue'
import {
  getDuctileFractureFigure,
  getDuctileFractureImage,
  getDuctileFractureSpecimenImage
} from '@/utils/component'
import type { DuctileFracturePlotId } from '@/utils/ductile_fracture'
import { formatNumber } from '@/utils/formatter'
import { mdiMagnifyPlusOutline } from '@mdi/js'
import { computed, ref, watch } from 'vue'

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

// The geometry drawing is generated per specimen (make precompute-fracture-figures)
// and committed, so a specimen added to the data repo since the last run has none.
// Fall back to the sketch of its geometry family, then to the generic placeholder.
const figureFailed = ref(false)
watch(
  () => props.ductileFracture.id,
  () => (figureFailed.value = false)
)
const figureSrc = computed(() =>
  figureFailed.value
    ? getDuctileFractureSpecimenImage(props.ductileFracture.specimen_type) ??
      getDuctileFractureImage()
    : getDuctileFractureFigure(props.ductileFracture.id)
)
</script>

<template>
  <common-detail
    database-id="ductile-fracture"
    :record="ductileFracture"
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
        <v-col cols="12" :sm="twoFigures ? 6 : 12">
          <ductile-fracture-plot-slot
            v-if="leftOptions.length > 0"
            :model="ductileFracture"
            :options="leftOptions"
            :default-plot="leftOptions[0]"
          />
        </v-col>
        <v-col v-if="twoFigures" cols="12" sm="6">
          <ductile-fracture-plot-slot
            :model="ductileFracture"
            :options="rightOptions"
            :default-plot="rightOptions[0]"
          />
        </v-col>
      </v-row>
      <v-row>
        <v-col cols="12" sm="6">
          <div class="mb-5">
            <h2 class="mb-2">{{ $t('detail.ductile_fracture.structural_steel_element') }}</h2>
            <p>
              <property-item
                column="location_coupon"
                :name="$t('detail.ductile_fracture.coupon_location')"
              >
                {{ ductileFracture.location_coupon }}
              </property-item>
              <property-item
                column="section_profile"
                :name="$t('detail.ductile_fracture.section_profile')"
              >
                {{ ductileFracture.section_profile }}
              </property-item>
              <property-item
                column="plate_thickness"
                :name="$t('detail.ductile_fracture.plate_thickness')"
                unit="mm"
              >
                {{ formatNumber(ductileFracture, 'plate_thickness') }}
              </property-item>
              <property-item
                column="temperature"
                :name="$t('detail.ductile_fracture.temperature')"
                unit="°C"
              >
                {{ formatNumber(ductileFracture, 'temperature') }}
              </property-item>
            </p>
          </div>
          <div class="mb-5">
            <h2 class="mb-2">{{ $t('detail.ductile_fracture.steel_material_designation') }}</h2>
            <p>
              <property-item column="steel_type" :name="$t('detail.ductile_fracture.steel_type')">
                {{ ductileFracture.steel_type }}
              </property-item>
              <property-item
                column="f_yn"
                :name="$t('detail.ductile_fracture.nominal_yield_stress')"
                unit="MPa"
              >
                {{ formatNumber(ductileFracture, 'f_yn') }}
              </property-item>
              <property-item
                column="fy_m"
                :name="$t('detail.ductile_fracture.measured_yield_stress')"
                unit="MPa"
              >
                {{ formatNumber(ductileFracture, 'fy_m') }}
              </property-item>
              <property-item
                column="f_un"
                :name="$t('detail.ductile_fracture.nominal_ultimate_stress')"
                unit="MPa"
              >
                {{ formatNumber(ductileFracture, 'f_un') }}
              </property-item>
              <property-item
                column="fu_m"
                :name="$t('detail.ductile_fracture.measured_ultimate_stress')"
                unit="MPa"
              >
                {{ formatNumber(ductileFracture, 'fu_m') }}
              </property-item>
            </p>
          </div>
          <div class="mb-5">
            <h2 class="mb-2">{{ $t('detail.ductile_fracture.fracture_model_parameters') }}</h2>
            <p>
              <property-item column="swdfm_C" name="SWDFM C">
                {{ formatNumber(ductileFracture, 'swdfm_C', 3) }}
              </property-item>
              <property-item column="swdfm_kappa" name="SWDFM κ">
                {{ formatNumber(ductileFracture, 'swdfm_kappa', 3) }}
              </property-item>
              <property-item column="swdfm_beta" name="SWDFM β">
                {{ formatNumber(ductileFracture, 'swdfm_beta', 3) }}
              </property-item>
              <property-item column="cvgm_etamono" name="CVGM η">
                {{ formatNumber(ductileFracture, 'cvgm_etamono', 3) }}
              </property-item>
              <property-item column="cvgm_lambda" name="CVGM λ">
                {{ formatNumber(ductileFracture, 'cvgm_lambda', 3) }}
              </property-item>
              <property-item
                column="l_star"
                :name="$t('detail.ductile_fracture.characteristic_length')"
                unit="mm"
              >
                {{ formatNumber(ductileFracture, 'l_star', 3) }}
              </property-item>
            </p>
          </div>
        </v-col>
        <v-col cols="12" sm="6">
          <zoomable-image
            :src="figureSrc"
            :alt="$t('detail.ductile_fracture.figure_alt')"
            @error="figureFailed = true"
          />
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
