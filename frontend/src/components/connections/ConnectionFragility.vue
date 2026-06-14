<script setup lang="ts">
// Computations from https://github.com/RESSLab-Team/resslab-hub-scripts/tree/main/fragility_curves_steel_connections
//
// Layout: EPFL design handoff "Fragility A" — three-pane (controls + schematic
// left) with one full-width FOCUS chart and Pre-/Post-Northridge preview
// thumbnails below. Inputs use the EPFL tool controls (ToolSegmented / ToolSwitch
// / ToolSlider); the curves stay on the existing ECharts UnitChart wrapper.
import UnitChart from '@/components/commons/charts/UnitChart.vue'
import PageHeader from '@/components/commons/PageHeader.vue'
import UnitToggle from '@/components/commons/UnitToggle.vue'
import ToolSegmented from '@/components/commons/tools/ToolSegmented.vue'
import ToolSlider from '@/components/commons/tools/ToolSlider.vue'
import ToolSwitch from '@/components/commons/tools/ToolSwitch.vue'

import { publicPath } from '@/utils/common'
import { fragilityCurve } from '@/utils/fragility'
import { getColorMap } from '@/utils/vuetify'
import { MAX_ECHARTS_POINTS, sampleArray } from '@/utils/echarts'
import type { EChartsOption } from 'echarts'
import { computed, reactive, ref } from 'vue'

type FocusId = 'pre' | 'post'
interface Variables {
  l: number
  db: number
}

const materials: { value: string; text: string }[] = [
  { value: 'a36', text: 'ASTM A36' },
  { value: 'a572', text: 'ASTM A572' }
]

const infoAvailable = ref(true)
const material = ref('a36')
const focus = ref<FocusId>('pre')
const variables = reactive<Variables>({ l: 4000, db: 600 })

const preNorthridgeOption = computed<EChartsOption>(() => {
  const { l, db } = variables

  let yieldingMedian: number
  let yieldingSigma: number
  let fractureMedian: number
  let fractureSigma: number
  if (infoAvailable.value) {
    yieldingMedian =
      material.value === 'a36'
        ? Math.exp(-1.83 + 0.16 * (l / db))
        : Math.exp(-0.56 + 0.028 * (l / db))
    yieldingSigma = material.value === 'a36' ? 0.24 : 0.18
    fractureMedian = Math.exp(0.99 - 0.0074 * (db / 10))
    fractureSigma = 0.44
  } else {
    yieldingMedian = material.value === 'a36' ? 0.77 : 0.76
    yieldingSigma = material.value === 'a36' ? 0.32 : 0.19
    fractureMedian = 1.85
    fractureSigma = 0.47
  }
  return {
    xAxis: { name: 'SDR' },
    yAxis: { name: 'P(DS)' },
    color: getColorMap(2),
    series: [
      {
        type: 'line',
        name: 'Yielding',
        showSymbol: false,
        data: sampleArray(fragilityCurve(yieldingMedian, yieldingSigma), MAX_ECHARTS_POINTS)
      },
      {
        type: 'line',
        name: 'Brittle Fracture',
        showSymbol: false,
        data: sampleArray(fragilityCurve(fractureMedian, fractureSigma), MAX_ECHARTS_POINTS)
      }
    ]
  }
})

const postNorthridgeOption = computed<EChartsOption>(() => {
  return {
    xAxis: { name: 'SDR' },
    yAxis: { name: 'P(DS)' },
    color: getColorMap(5),
    series: [
      { type: 'line', name: 'Yielding Anywhere', showSymbol: false, data: fragilityCurve(1, 0.17) },
      {
        type: 'line',
        name: 'Yielding @ Panel Zone',
        showSymbol: false,
        data: fragilityCurve(1, 0.15)
      },
      {
        type: 'line',
        name: 'Yielding @ Flanges',
        showSymbol: false,
        data: fragilityCurve(0.96, 0.1)
      },
      { type: 'line', name: 'Local Buckling', showSymbol: false, data: fragilityCurve(2.16, 0.3) },
      { type: 'line', name: 'Ductile Tearing', showSymbol: false, data: fragilityCurve(5, 0.31) }
    ]
  }
})

const panels = computed<{ id: FocusId; title: string; option: EChartsOption }[]>(() => [
  { id: 'pre', title: 'Pre-Northridge', option: preNorthridgeOption.value },
  { id: 'post', title: 'Post-Northridge', option: postNorthridgeOption.value }
])
const activePanel = computed(() => panels.value.find((p) => p.id === focus.value)!)

// Compact, label-free clone for the preview thumbnails; inactive series go grey.
function thumbOption(option: EChartsOption, active: boolean): EChartsOption {
  const series = option.series as { type: string }[]
  return {
    ...option,
    grid: { left: 8, right: 8, top: 8, bottom: 8, containLabel: false },
    xAxis: { ...(option.xAxis as object), name: '', axisLabel: { show: false } },
    yAxis: { ...(option.yAxis as object), name: '', axisLabel: { show: false } },
    color: active ? (option.color as string[]) : series.map(() => '#c1c1c1'),
    legend: { show: false }
  }
}
</script>

<template>
  <div class="tool-page">
    <page-header
      eyebrow="Tools · Fragility curves"
      title="Fragility Curve Plotter for Steel Components"
    >
      <template #actions><unit-toggle /></template>
      This tab introduces a web-based interactive module for visualizing fragility curves of Pre-
      and Post-Northridge beam-to-column connections. For further information refer to
      <a
        href="https://ascelibrary.org/doi/abs/10.1061/%28ASCE%29ST.1943-541X.0000214"
        target="_blank"
        >Lignos et al. (2010)</a
      >
      and
      <a
        href="https://www.sciencedirect.com/science/article/abs/pii/S0141029612003689"
        target="_blank"
        >Ramirez et al. (2012)</a
      >.
    </page-header>

    <div class="tool-shell">
      <div class="frag-a">
        <aside class="tool-panel">
          <div class="tool-card">
            <div class="tfield">
              <div class="tfield-label">Steel Type</div>
              <tool-segmented v-model="material" full :items="materials" />
            </div>
            <div class="tfield">
              <div class="tfield-label">Geometric Parameters</div>
              <tool-switch v-model="infoAvailable" label="Parameters available" />
            </div>
            <div class="tfield">
              <tool-slider
                v-model="variables.l"
                :disabled="!infoAvailable"
                label="L"
                :max="12000"
                :min="1000"
                :step="50"
                unit="mm"
              />
            </div>
            <div class="tfield">
              <tool-slider
                v-model="variables.db"
                :disabled="!infoAvailable"
                label="d<sub>b</sub>"
                :max="2000"
                :min="100"
                :step="10"
                unit="mm"
              />
            </div>
            <div class="tfield-ratio">
              <span>L / d<sub>b</sub></span>
              <strong>{{ (variables.l / variables.db).toFixed(2) }}</strong>
            </div>
          </div>
          <figure class="tool-schematic">
            <img
              alt="Beam-to-column connection fragility schematic"
              :src="publicPath + 'img/connection/connection_fragility.png'"
            />
            <figcaption>
              Pre-Northridge beam-to-column moment connection — definition of L and d<sub>b</sub>.
            </figcaption>
          </figure>
        </aside>

        <section class="tool-chart-col">
          <div class="mat-focus">
            <h2 class="tool-chart-h">{{ activePanel.title }}</h2>
            <unit-chart :aspect-ratio="2.2" :option="activePanel.option" x-unit="rad" />
          </div>
          <div class="mat-thumbs frag-thumbs">
            <button
              v-for="panel in panels"
              :key="panel.id"
              class="mat-thumb"
              :class="{ 'is-active': focus === panel.id }"
              type="button"
              @click="focus = panel.id"
            >
              <div class="mat-thumb-chart">
                <unit-chart
                  :aspect-ratio="3"
                  :option="thumbOption(panel.option, focus === panel.id)"
                  x-unit="rad"
                />
              </div>
              <span class="mat-thumb-label">{{ panel.title }}</span>
            </button>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>
