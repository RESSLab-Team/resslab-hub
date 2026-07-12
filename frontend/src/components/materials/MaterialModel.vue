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
import ToolShell from '@/components/commons/ToolShell.vue'
import type { Variable } from '@/utils/model'
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
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })

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
const variableGroups = computed<{ name: string; keys: (keyof Material)[] }[]>(() => [
  { name: t('tools.material_model.group_elastic'), keys: ['e'] },
  { name: t('tools.material_model.group_isotropic'), keys: ['sigma', 'q', 'b', 'd', 'a'] },
  { name: t('tools.material_model.group_kinematic'), keys: ['c1', 'gamma1', 'c2', 'gamma2'] }
])
function variableByKey(key: keyof Material): Variable<keyof Material> {
  return materialVariables.find((v) => v.key === key)!
}

type testId = 'LP1_S1_C' | 'LP6_S1_C' | 'LP9_S1_D' | 'LP5_S1_D'
const charts = computed<{ title: string; id: testId }[]>(() => [
  { title: t('tools.material_model.protocol_monotonic_tensile'), id: 'LP1_S1_C' },
  { title: t('tools.material_model.protocol_symmetric_cyclic'), id: 'LP6_S1_C' },
  { title: t('tools.material_model.protocol_random'), id: 'LP9_S1_D' },
  { title: t('tools.material_model.protocol_constant_amplitude'), id: 'LP5_S1_D' }
])

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

const focusTitle = computed(() => charts.value.find((c) => c.id === focus.value)!.title)

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

const paramCount = computed(() =>
  variableGroups.value.reduce((n, group) => n + group.keys.length, 0)
)
</script>

<template>
  <tool-shell
    :eyebrow="$t('tools.common.model_eyebrow')"
    :title="$t('tools.material_model.title')"
    :param-count="paramCount"
    stage-class="stage-d"
  >
    <template #actions><unit-toggle /></template>
    <template #intro>
      <i18n-t keypath="tools.material_model.intro" tag="span" scope="global">
        <template #hartloper>
          <a
            href="https://ascelibrary.org/doi/abs/10.1061/%28ASCE%29ST.1943-541X.0002964"
            target="_blank"
            >{{ $t('tools.material_model.intro_hartloper') }}</a
          >
        </template>
        <template #castro>
          <a
            href="https://ascelibrary.org/doi/full/10.1061/%28ASCE%29EM.1943-7889.0001922"
            target="_blank"
            >{{ $t('tools.material_model.intro_castro') }}</a
          >
        </template>
      </i18n-t>
    </template>

    <template #rail>
      <div class="tool-card">
        <div class="tool-card-h with-info">
          {{ $t('tools.material_model.select_steel_material') }}
          <info-tooltip>{{ $t('tools.material_model.select_steel_material_help') }}</info-tooltip>
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
    </template>

    <template #stage>
      <div class="st-block st-chart">
        <div class="chart-cap">
          <h2 class="chart-h">{{ focusTitle }}</h2>
        </div>
        <div class="tchart h-chart">
          <unit-line-chart
            fill
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
      </div>
    </template>
  </tool-shell>
</template>
