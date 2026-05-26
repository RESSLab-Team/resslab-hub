<script setup lang="ts">
import type { DuctileFractureModel } from '@/backend'
import UnitLineChart from '@/components/commons/charts/UnitLineChart.vue'
import {
  ductileFracturePlots,
  type DuctileFracturePlotId
} from '@/utils/ductile_fracture'
import type { LineSeriesOption } from 'echarts'
import { computed, ref, watch } from 'vue'

const props = defineProps<{
  model: DuctileFractureModel
  options: DuctileFracturePlotId[]
  defaultPlot: DuctileFracturePlotId
  aspectRatio?: number
}>()

const selected = ref<DuctileFracturePlotId>(props.defaultPlot)

watch(
  () => [props.model.id, props.defaultPlot, props.options] as const,
  ([, defaultPlot, options]) => {
    if (!options.includes(selected.value)) {
      selected.value = defaultPlot
    }
  }
)

const config = computed(() => ductileFracturePlots[selected.value])

const optionItems = computed(() =>
  props.options.map((id) => ({ value: id, title: ductileFracturePlots[id].title }))
)

const series = ref<LineSeriesOption[]>([])

watch(
  [() => props.model.id, selected],
  async ([id, plotId]) => {
    const cfg = ductileFracturePlots[plotId]
    const wantTest = !!cfg.testFetcher && cfg.hasTest(props.model)
    const wantSim = !!cfg.simulationFetcher && cfg.hasSimulation(props.model)

    series.value = []

    const [testResp, simResp] = await Promise.all([
      wantTest ? cfg.testFetcher!(id) : Promise.resolve(null),
      wantSim ? cfg.simulationFetcher!(id) : Promise.resolve(null)
    ])

    if (selected.value !== plotId || props.model.id !== id) return

    const next: LineSeriesOption[] = []
    if (testResp && simResp) {
      next.push({ name: 'Test Data', data: testResp.data })
      next.push({ name: 'Simulation', data: simResp.data })
    } else if (testResp) {
      next.push({ data: testResp.data })
    } else if (simResp) {
      next.push({ data: simResp.data })
    }
    series.value = next
  },
  { immediate: true }
)
</script>

<template>
  <div>
    <v-select
      v-if="options.length > 1"
      v-model="selected"
      :items="optionItems"
      density="compact"
      hide-details
      variant="outlined"
      class="mb-2"
    />
    <unit-line-chart
      :title="config.title"
      :x-axis-name="config.xAxisName"
      :y-axis-name="config.yAxisName"
      :series="series"
      :aspect-ratio="aspectRatio ?? 1.5"
    />
  </div>
</template>
