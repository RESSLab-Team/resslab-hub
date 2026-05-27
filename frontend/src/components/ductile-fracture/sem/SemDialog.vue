<script setup lang="ts">
import type { DuctileFractureModel } from '@/backend'
import SemCdfChart from '@/components/ductile-fracture/sem/SemCdfChart.vue'
import SemHotspots from '@/components/ductile-fracture/sem/SemHotspots.vue'
import {
  SEM_MAGNIFICATIONS,
  semGlobalImageUrl,
  semLocalImageUrl,
  type SemLocation,
  type SemMagnification
} from '@/utils/sem'
import { mdiArrowLeft, mdiClose } from '@mdi/js'
import { computed, ref, watch } from 'vue'

const props = defineProps<{
  modelValue: boolean
  model: DuctileFractureModel
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const dialogOpen = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v)
})

const selectedLocation = ref<SemLocation | undefined>(undefined)
const selectedMagnification = ref<SemMagnification | undefined>(undefined)

const imageUrl = computed(() =>
  selectedLocation.value && selectedMagnification.value
    ? semLocalImageUrl(props.model.id, selectedLocation.value, selectedMagnification.value)
    : semGlobalImageUrl(props.model.id)
)

const isGlobalView = computed(() => !selectedLocation.value)

function resetToGlobal() {
  selectedLocation.value = undefined
  selectedMagnification.value = undefined
}

function onHotspot(location: SemLocation, magnification: SemMagnification) {
  selectedLocation.value = location
  selectedMagnification.value = magnification
}

function onMagnification(mag: SemMagnification) {
  selectedMagnification.value = mag
}

watch(
  () => props.model.id,
  () => resetToGlobal()
)
watch(dialogOpen, (open) => {
  if (!open) resetToGlobal()
})
</script>

<template>
  <v-dialog v-model="dialogOpen" width="85vw" max-width="none" max-height="90vh" scrollable>
    <v-card rounded="lg">
      <v-card-title class="d-flex align-center pa-4">
        <span class="text-h6">
          Scanning Electron Microscopy — {{ model.specimen_designation }}
        </span>
        <v-spacer />
        <v-btn :icon="mdiClose" variant="text" density="comfortable" @click="dialogOpen = false" />
      </v-card-title>
      <v-divider />
      <v-card-text class="pa-6">
        <v-row dense>
          <v-col cols="12" md="6">
            <div class="d-flex align-center flex-wrap ga-2 mb-3" style="min-height: 36px">
              <v-btn
                variant="tonal"
                size="small"
                :prepend-icon="mdiArrowLeft"
                class="text-none"
                :disabled="isGlobalView"
                @click="resetToGlobal"
              >
                Global
              </v-btn>
              <template v-if="!isGlobalView">
                <v-divider vertical class="mx-2" />
                <span class="text-body-2 font-weight-medium text-capitalize">
                  {{ selectedLocation }}
                </span>
                <v-btn-toggle
                  :model-value="selectedMagnification"
                  density="compact"
                  mandatory
                  divided
                  color="primary"
                  variant="outlined"
                  class="ml-2"
                  @update:model-value="onMagnification"
                >
                  <v-btn v-for="mag in SEM_MAGNIFICATIONS" :key="mag" :value="mag" size="small">
                    {{ mag }}×
                  </v-btn>
                </v-btn-toggle>
              </template>
              <span v-else class="text-caption text-medium-emphasis ml-2">
                Hover a magnifier to pick a zoom level.
              </span>
            </div>
            <div class="sem-image-wrap">
              <v-img
                :src="imageUrl"
                :alt="String(selectedLocation ?? 'global')"
                contain
                max-height="65vh"
              />
              <sem-hotspots
                v-if="isGlobalView"
                :specimen-type="model.specimen_type"
                @select="onHotspot"
              />
            </div>
          </v-col>
          <v-col cols="12" md="6">
            <sem-cdf-chart
              :ductile-fracture-id="model.id"
              :location="selectedLocation"
              :magnification="selectedMagnification"
            />
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.sem-image-wrap {
  position: relative;
}
</style>
