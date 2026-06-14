<script setup lang="ts">
// Layout: EPFL design handoff "Material A" — split, with the left column as a
// grouped parameter rail (Elastic / Isotropic / Kinematic) and the right side a
// large FOCUS chart with a 2×2 grid of switchable protocol previews. Inputs use
// the EPFL tool controls (ToolSelect / ToolSlider); the σ–ε curves stay on the
// existing ECharts wrappers and the UVC computation is unchanged.
import materialParameters from '@/assets/material/parameter-material-list.csv'
import UnitChart from '@/components/commons/charts/UnitChart.vue'
import UnitLineChart from '@/components/commons/charts/UnitLineChart.vue'
import InfoTooltip from '@/components/commons/InfoTooltip.vue'
import PageHeader from '@/components/commons/PageHeader.vue'
import type { Variable } from '@/components/commons/sliders/UnitSlider.vue'
import UnitToggle from '@/components/commons/UnitToggle.vue'
import ToolSelect from '@/components/commons/tools/ToolSelect.vue'
import ToolSlider from '@/components/commons/tools/ToolSlider.vue'
import { materialsApi } from '@/plugins/axios'
import { useNotificationStore } from '@/stores/notification'
import { computeUvcStress } from '@/utils/material'
import type { SelectItemObject } from '@/utils/vuetify'
import type { EChartsOption, LineSeriesOption } from 'echarts'
import { zip } from 'lodash'
import { computed, onMounted, reactive, ref, watch } from 'vue'

interface Material {
  e: number
  sigma: number
  q: number
  b: number
  d: number
  a: number
  c1: number
  gamma1: number
  c2: number
  gamma2: number
}

const materialSelectItems: SelectItemObject<Material>[] = materialParameters.map((item) => ({
  title: item.steel,
  value: {
    e: item.E,
    sigma: item.syo,
    q: item.Q_inf,
    b: item.b,
    d: item.D_inf,
    a: item.a,
    c1: item.c1,
    gamma1: item.gamma1,
    c2: item.c2,
    gamma2: item.gamma2
  } as Material
}))
const materialOptions = materialSelectItems.map((item) => ({
  title: String(item.title),
  value: String(item.title)
}))

const materialVariables: Variable<keyof Material>[] = [
  { key: 'e', text: 'E', unit: 'MPa', min: 190000, max: 210000 },
  { key: 'sigma', text: 'σ<sub>y0</sub>', min: 200, max: 700, unit: 'MPa' },
  { key: 'q', text: 'Q<sub>00</sub>', min: 0, max: 300, unit: 'MPa' },
  { key: 'b', text: 'b', min: 0, max: 30 },
  { key: 'd', text: 'D<sub>00</sub>', min: 0, max: 200, unit: 'MPa' },
  { key: 'a', text: 'a', min: 100, max: 400 },
  { key: 'c1', text: 'c<sub>1</sub>', min: 5000, max: 40000, unit: 'MPa' },
  { key: 'gamma1', text: 'γ<sub>1</sub>', min: 100, max: 400 },
  { key: 'c2', text: 'c<sub>2</sub>', min: 0, max: 5000, unit: 'MPa' },
  { key: 'gamma2', text: 'γ<sub>2</sub>', min: 0, max: 50 }
]

// Grouped parameter rail.
const variableGroups: { name: string; keys: (keyof Material)[] }[] = [
  { name: 'Elastic', keys: ['e'] },
  { name: 'Isotropic hardening', keys: ['sigma', 'q', 'b', 'd', 'a'] },
  { name: 'Kinematic hardening', keys: ['c1', 'gamma1', 'c2', 'gamma2'] }
]
function variableByKey(key: keyof Material): Variable<keyof Material> {
  return materialVariables.find((v) => v.key === key)!
}

type testId = 'LP1_S1_C' | 'LP6_S1_C' | 'LP9_S1_D' | 'LP5_S1_D'
const charts: { title: string; id: testId }[] = [
  { title: 'Monotonic Tensile', id: 'LP1_S1_C' },
  { title: 'Symmetric Cyclic', id: 'LP6_S1_C' },
  { title: 'Random', id: 'LP9_S1_D' },
  { title: 'Constant Amplitude', id: 'LP5_S1_D' }
]

const FOCUS_COLOR = '#a5add8'
const MUTED_COLOR = '#c1c1c1'

const notificationStore = useNotificationStore()

const selectedSteel = ref(String(materialSelectItems[0].title))
const focus = ref<testId>('LP6_S1_C')
const variables = reactive<Material>({
  e: 0,
  sigma: 0,
  q: 0,
  b: 0,
  d: 0,
  a: 0,
  c1: 0,
  gamma1: 0,
  c2: 0,
  gamma2: 0
})
const strains = ref<Record<testId, number[]>>({
  LP1_S1_C: [],
  LP6_S1_C: [],
  LP9_S1_D: [],
  LP5_S1_D: []
})

const chartSeries = computed<Record<testId, LineSeriesOption>>(() => {
  const { e, sigma, q, b, d, a, c1, gamma1, c2, gamma2 } = variables
  return Object.fromEntries(
    Object.entries(strains.value).map(([id, strain]) => {
      try {
        const stress = computeUvcStress(strain, e, sigma, q, b, d, a, [
          { c: c1, gamma: gamma1 },
          { c: c2, gamma: gamma2 }
        ])
        return [id, { data: zip(strain, stress) } as LineSeriesOption]
      } catch (error) {
        notificationStore.notify(error as string)
        return [id, { data: [[]] } as LineSeriesOption]
      }
    })
  ) as Record<testId, LineSeriesOption>
})

const focusTitle = computed(() => charts.find((c) => c.id === focus.value)!.title)

// Series with explicit colour: active focus is periwinkle, previews muted grey.
function styledSeries(id: testId, active: boolean): LineSeriesOption {
  return {
    ...chartSeries.value[id],
    type: 'line',
    showSymbol: false,
    lineStyle: { color: active ? FOCUS_COLOR : MUTED_COLOR },
    itemStyle: { color: active ? FOCUS_COLOR : MUTED_COLOR }
  }
}

// Compact, axis-free preview so the hysteresis shape fills the thumbnail.
function thumbOption(id: testId, active: boolean): EChartsOption {
  return {
    grid: { left: 6, right: 6, top: 6, bottom: 6, containLabel: false },
    xAxis: { type: 'value', name: '', axisLabel: { show: false } },
    yAxis: { type: 'value', name: '', axisLabel: { show: false } },
    series: [styledSeries(id, active)]
  }
}

onMounted(() => {
  Promise.all(
    Object.keys(strains.value).map((id) =>
      materialsApi
        .getMaterialsStressStrain(id)
        .then((response) => [id, response.data.map((serie) => serie[1])] as [testId, number[]])
    )
  ).then((entries) => (strains.value = Object.fromEntries(entries) as Record<testId, number[]>))
})

watch(
  selectedSteel,
  (steel) => {
    const item = materialSelectItems.find((m) => String(m.title) === steel)
    if (item) {
      Object.assign(variables, item.value)
    }
  },
  { immediate: true }
)
</script>

<template>
  <div class="tool-page">
    <page-header eyebrow="Tools · Component model" title="Material Model">
      <template #actions><unit-toggle /></template>
      This web based interactive interface computes the hysteretic behavior of typical steels under
      inelastic cyclic straining. For further information refer to
      <a
        href="https://ascelibrary.org/doi/abs/10.1061/%28ASCE%29ST.1943-541X.0002964"
        target="_blank"
        >Hartloper et al. (2021)</a
      >
      The uniaxial loading protocols are based on work by
      <a
        href="https://ascelibrary.org/doi/full/10.1061/%28ASCE%29EM.1943-7889.0001922"
        target="_blank"
        >de Castro e Sousa et al. (2020)</a
      >
    </page-header>

    <div class="tool-shell">
      <div class="mat-a">
        <section class="tool-panel">
          <div class="tool-card">
            <div class="tool-card-h with-info">
              Select Steel Material
              <info-tooltip>
                Here you can select a steel material from the available list and with the sliders
                below you can check the sensitivity of the updated Voce and Chaboche constitutive
                model to the input material model parameters. The model is displayed based on four
                selected strain-based protocols for the same set of input model parameters.
              </info-tooltip>
            </div>
            <tool-select v-model="selectedSteel" :items="materialOptions" />
            <div class="mat-a-groups">
              <div v-for="group in variableGroups" :key="group.name" class="tool-param-group">
                <div class="tool-param-group-h">{{ group.name }}</div>
                <tool-slider
                  v-for="key in group.keys"
                  :key="key"
                  v-model="variables[key]"
                  :label="variableByKey(key).text"
                  :max="variableByKey(key).max"
                  :min="variableByKey(key).min"
                  :unit="variableByKey(key).unit"
                />
              </div>
            </div>
          </div>
        </section>

        <section class="mat-focus-col">
          <div class="mat-focus">
            <div class="mat-chart-h">{{ focusTitle }}</div>
            <unit-line-chart
              :aspect-ratio="2"
              :series="[styledSeries(focus, true)]"
              x-axis-name="ε"
              y-axis-name="σ"
              y-unit="MPa"
            />
          </div>
          <div class="mat-thumbs">
            <button
              v-for="item in charts"
              :key="item.id"
              class="mat-thumb"
              :class="{ 'is-active': focus === item.id }"
              type="button"
              @click="focus = item.id"
            >
              <div class="mat-thumb-chart">
                <unit-chart :aspect-ratio="1.9" :option="thumbOption(item.id, focus === item.id)" />
              </div>
              <span class="mat-thumb-label">{{ item.title }}</span>
            </button>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>
