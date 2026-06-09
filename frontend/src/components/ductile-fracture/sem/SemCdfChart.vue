<script setup lang="ts">
import UnitLineChart from '@/components/commons/charts/UnitLineChart.vue'
import {
  computeCdf,
  fetchDimples,
  semDimplesUrl,
  type SemLocation,
  type SemMagnification
} from '@/utils/sem'
import type { LineSeriesOption } from 'echarts'
import { ref, watch } from 'vue'

const props = defineProps<{
  ductileFractureId: string
  location?: SemLocation
  magnification?: SemMagnification
}>()

const series = ref<LineSeriesOption[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

watch(
  () => [props.ductileFractureId, props.location, props.magnification] as const,
  async ([id, location, magnification]) => {
    loading.value = true
    error.value = null
    series.value = []
    try {
      const url = semDimplesUrl(id, location, magnification)
      const diameters = await fetchDimples(url)
      series.value = [{ data: computeCdf(diameters) }]
    } catch (e) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  },
  { immediate: true }
)
</script>

<template>
  <div>
    <unit-line-chart
      title="Dimple diameter CDF"
      x-axis-name="Dimple diameter [mm]"
      y-axis-name="CDF"
      :series="series"
      :aspect-ratio="1.2"
    />
    <v-alert v-if="error" type="warning" density="compact" class="mt-2">
      Failed to load dimple data ({{ error }}).
    </v-alert>
  </div>
</template>
