<script setup lang="ts">
import {
  hotspotsFor,
  SEM_MAGNIFICATIONS,
  type HotspotPosition,
  type SemLocation,
  type SemMagnification
} from '@/utils/sem'
import { mdiMagnifyPlusOutline } from '@mdi/js'
import { computed } from 'vue'

const props = defineProps<{
  specimenType: string
  locations?: SemLocation[]
}>()

const emit = defineEmits<{
  (e: 'select', location: SemLocation, magnification: SemMagnification): void
}>()

const hotspots = computed(
  () => hotspotsFor(props.specimenType, props.locations) as Record<SemLocation, HotspotPosition>
)
</script>

<template>
  <div class="sem-hotspots">
    <v-menu
      v-for="(pos, location) in hotspots"
      :key="location"
      open-on-hover
      location="end center"
      :open-delay="50"
      :close-delay="120"
    >
      <template #activator="{ props: menuProps }">
        <v-btn
          v-bind="menuProps"
          :icon="mdiMagnifyPlusOutline"
          size="small"
          color="white"
          variant="elevated"
          density="comfortable"
          class="sem-hotspot"
          :style="{ left: `${pos.x}%`, top: `${pos.y}%` }"
          :title="String(location)"
        />
      </template>
      <v-card density="compact" rounded="pill" class="pa-1">
        <v-btn-group density="compact" divided variant="text">
          <v-btn
            v-for="mag in SEM_MAGNIFICATIONS"
            :key="mag"
            size="small"
            @click="emit('select', location as SemLocation, mag)"
          >
            {{ mag }}×
          </v-btn>
        </v-btn-group>
      </v-card>
    </v-menu>
  </div>
</template>

<style scoped>
.sem-hotspots {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.sem-hotspot {
  position: absolute;
  transform: translate(-50%, -50%);
  pointer-events: auto;
  color: rgb(var(--v-theme-primary));
}
</style>
