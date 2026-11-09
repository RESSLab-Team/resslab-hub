<script setup lang="ts">
import type { DuctileFractureModel } from '@/backend'
import SemCdfChart from '@/components/ductile-fracture/sem/SemCdfChart.vue'
import SemHotspots from '@/components/ductile-fracture/sem/SemHotspots.vue'
import {
  fetchSemManifest,
  SEM_MAGNIFICATIONS,
  semGlobalImageUrl,
  semLocalImageUrl,
  type SemLocation,
  type SemManifest,
  type SemMagnification
} from '@/utils/sem'
import { mdiArrowLeft, mdiClose } from '@mdi/js'
import { computed, ref, watch } from 'vue'
import { useDisplay } from 'vuetify'

const props = defineProps<{
  modelValue: boolean
  model: DuctileFractureModel
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const { xs } = useDisplay()

const dialogOpen = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v)
})

const selectedLocation = ref<SemLocation | undefined>(undefined)
const selectedMagnification = ref<SemMagnification | undefined>(undefined)
const selectedSurface = ref(1)
const manifest = ref<SemManifest | undefined>(undefined)

// Ruptured-bar coupons (Ozden et al.) are imaged on both fracture surfaces; the
// manifest reports how many and which locations exist for this specimen.
const surfaceCount = computed(() => manifest.value?.surfaces ?? 1)

const imageUrl = computed(() =>
  selectedLocation.value && selectedMagnification.value
    ? semLocalImageUrl(
        props.model.id,
        selectedLocation.value,
        selectedMagnification.value,
        selectedSurface.value
      )
    : semGlobalImageUrl(props.model.id, selectedSurface.value)
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

function onSurface(surface: number) {
  selectedSurface.value = surface
  resetToGlobal()
}

async function loadManifest(id: string) {
  manifest.value = undefined
  try {
    manifest.value = await fetchSemManifest(id)
  } catch {
    // Older single-surface specimens may predate the manifest; treat as one
    // surface with the full hotspot set for the specimen type.
    manifest.value = undefined
  }
}

watch(
  () => props.model.id,
  (id) => {
    selectedSurface.value = 1
    resetToGlobal()
    if (dialogOpen.value) loadManifest(id)
  }
)
watch(dialogOpen, (open) => {
  if (open) {
    loadManifest(props.model.id)
  } else {
    selectedSurface.value = 1
    resetToGlobal()
  }
})
</script>

<template>
  <!-- Full screen on a phone: at 85vw the image and the chart are too small. -->
  <v-dialog
    v-model="dialogOpen"
    width="85vw"
    max-width="none"
    max-height="90vh"
    :fullscreen="xs"
    scrollable
  >
    <v-card rounded="lg">
      <v-card-title class="d-flex align-center pa-4">
        <span class="text-h6">
          {{ $t('sem.dialog_title', { id: model.specimen_designation }) }}
        </span>
        <v-spacer />
        <v-btn
          :icon="mdiClose"
          :aria-label="$t('commons.close')"
          variant="text"
          density="comfortable"
          @click="dialogOpen = false"
        />
      </v-card-title>
      <v-divider />
      <v-card-text class="pa-4 pa-sm-6">
        <v-row dense>
          <v-col cols="12" md="6">
            <div v-if="surfaceCount > 1" class="d-flex align-center flex-wrap ga-2 mb-3">
              <span class="text-body-2 font-weight-medium">Fracture surface</span>
              <v-btn-toggle
                :model-value="selectedSurface"
                density="compact"
                mandatory
                divided
                color="primary"
                variant="outlined"
                @update:model-value="onSurface"
              >
                <v-btn v-for="s in surfaceCount" :key="s" :value="s" size="small">
                  {{ s }}
                </v-btn>
              </v-btn-toggle>
            </div>
            <div class="d-flex align-center flex-wrap ga-2 mb-3" style="min-height: 36px">
              <v-btn
                variant="tonal"
                size="small"
                :prepend-icon="mdiArrowLeft"
                class="text-none"
                :disabled="isGlobalView"
                @click="resetToGlobal"
              >
                {{ $t('sem.global') }}
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
                {{ $t('sem.hover_hint') }}
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
                :locations="manifest?.locations"
                @select="onHotspot"
              />
            </div>
          </v-col>
          <v-col cols="12" md="6">
            <sem-cdf-chart
              :ductile-fracture-id="model.id"
              :location="selectedLocation"
              :magnification="selectedMagnification"
              :surface="selectedSurface"
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
