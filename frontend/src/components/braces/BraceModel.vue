<script setup lang="ts">
import UnitChart from '@/components/commons/charts/UnitChart.vue'
import InfoTooltip from '@/components/commons/InfoTooltip.vue'
import PageHeader from '@/components/commons/PageHeader.vue'
import SectionSelector from '@/components/commons/SectionSelector.vue'
import ToolSelect from '@/components/commons/tools/ToolSelect.vue'
import ToolSlider from '@/components/commons/tools/ToolSlider.vue'
import type { Variable } from '@/utils/model'
import UnitToggle from '@/components/commons/UnitToggle.vue'
import { publicPath, type Section } from '@/utils/common'
import { primaryColor } from '@/utils/vuetify'
import type { EChartsOption } from 'echarts'
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import DisclaimerComponent from '@/components/commons/DisclaimerComponent.vue'

const { t } = useI18n()

type SteelType = 'S235' | 'S275' | 'S355' | 'S420' | 'S460'
type Option = 'wide-flange' | 'double-c' | 'double-l' | 'round' | 'square' | 'l-shape'
interface Result {
  delta_y: number
  delta_ut: number
  Nple: number
  delta_c: number
  delta_ub: number
  Nbe: number
  Nu_c: number
}

const steelTypes: SteelType[] = ['S235', 'S275', 'S355', 'S420', 'S460']
const steelTypeItems = steelTypes.map((value) => ({ title: value, value }))
const optionDefs: { value: Option; titleKey: string; disabled?: boolean }[] = [
  { value: 'wide-flange', titleKey: 'opt_wide_flange' },
  { value: 'double-c', titleKey: 'opt_double_c', disabled: true },
  { value: 'double-l', titleKey: 'opt_double_l', disabled: true },
  { value: 'round', titleKey: 'opt_round', disabled: true },
  { value: 'square', titleKey: 'opt_square', disabled: true },
  { value: 'l-shape', titleKey: 'opt_l_shape', disabled: true }
]
const optionItems = computed(() =>
  optionDefs.map((o) => ({
    title: t(`tools.brace_model.${o.titleKey}`),
    value: o.value as string,
    disabled: o.disabled
  }))
)
const steelShapeDimensions: Variable<keyof Variables>[] = [
  {
    key: 'bf',
    text: 'b<sub>f</sub>',
    unit: 'mm',
    min: 100,
    max: 500
  },
  { key: 'd', text: 'd', unit: 'mm', min: 100, max: 2000 },
  {
    key: 'tf',
    text: 't<sub>f</sub>',
    unit: 'mm',
    min: 5,
    max: 100
  },
  {
    key: 'tw',
    text: 't<sub>w</sub>',
    unit: 'mm',
    min: 5,
    max: 100
  }
]
const steelTypeVariables: Variable<keyof Variables>[] = [
  {
    key: 'omega',
    text: 'Ω',
    min: 1,
    max: 2
  },
  {
    key: 'fy',
    text: 'fy',
    unit: 'MPa',
    min: 250,
    max: 500
  }
]
const additionalParameterVariables: Variable<keyof Variables>[] = [
  {
    key: 'lee',
    text: 'Lee',
    min: 1000,
    max: 12000
  },
  {
    key: 'lcr',
    text: 'Lcr',
    min: 1000,
    max: 12000
  }
]

const section = ref<Section>()
const steelType = ref<SteelType>()
const option = ref<Option>('wide-flange')

const e = 210000
const a = 10000
const iz = 10000
const iy = 1000000
interface Variables {
  bf: number
  d: number
  tf: number
  tw: number
  omega: number
  fy: number
  lee: number
  lcr: number
}
const variables = reactive<Variables>({
  bf: 100,
  d: 100,
  tf: 5,
  tw: 5,
  omega: 1,
  fy: 250,
  lee: 8000,
  lcr: 8000
})

watch(
  steelType,
  (value) => {
    switch (value) {
      case 'S235':
        variables.omega = 1.45
        variables.fy = 235
        return
      case 'S275':
        variables.omega = 1.35
        variables.fy = 275
        return
      case 'S355':
        variables.omega = 1.25
        variables.fy = 255
        return
      case 'S420':
        variables.omega = 1.25
        variables.fy = 420
        return
      case 'S460':
        variables.omega = 1.2
        variables.fy = 460
        return
    }
  },
  {
    immediate: true
  }
)

const result = computed<Result>(() => {
  const { omega, fy, lcr } = variables

  const Imin = Math.min(iz, iy)
  const i = Math.sqrt(Imin / a)

  let lamda_f: number
  let lamda_CL1: number
  switch (option.value) {
    case 'wide-flange': {
      const c = 10
      const t = 2
      lamda_f = c / t
      lamda_CL1 = 9 * Math.sqrt(235 / fy)
      break
    }
    default:
      throw new Error(`Unhandled ${option.value}`)
  }
  const NbRd = 1
  const NplRd = 1
  const Nple = omega * NplRd
  const Nbe = omega * NbRd
  const Nu_c = 0.2 * omega * NbRd
  const delta_y = 1
  const delta_c = 1

  let delta_ub: number
  let delta_ut: number
  switch (option.value) {
    case 'wide-flange': {
      delta_ub =
        5.6 *
        Math.pow(lamda_f / lamda_CL1, -1.7) *
        Math.pow((lcr / i) * Math.sqrt((omega * fy) / e), 0.4) *
        delta_c
      delta_ut =
        3.4 *
        Math.pow(lamda_f / lamda_CL1, -1.7) *
        Math.pow((lcr / i) * Math.sqrt((omega * fy) / e), 0.4) *
        delta_y
      break
    }
    default:
      throw new Error(`Unhandled ${option.value}`)
  }

  return {
    delta_y: delta_y,
    delta_ut: delta_ut,
    Nple: Nple,
    delta_c: delta_c,
    delta_ub: delta_ub,
    Nbe: Nbe,
    Nu_c: Nu_c
  }
})

function onSectionChanged(value?: Section): void {
  section.value = value
  if (value) {
    variables.bf = value.bf
    variables.d = value.d
    variables.tf = value.tf
    variables.tw = value.tw
  }
}

function getTensionOption(result: Result): EChartsOption {
  return {
    xAxis: {
      name: t('tools.brace_model.tension_x_axis'),
      max: 1.2 * result.delta_ut
    },
    yAxis: {
      name: t('tools.brace_model.tension_y_axis'),
      max: 1.2 * result.Nple
    },
    series: [
      {
        type: 'line',
        data: [
          [0, 0],
          [result.delta_y, result.Nple],
          [result.delta_ut, result.Nple]
        ],
        color: primaryColor.base
      },
      {
        type: 'line',
        data: [
          [result.delta_ut, result.Nple],
          [result.delta_ut, 0]
        ],
        color: primaryColor.base,
        lineStyle: {
          type: 'dashed'
        }
      }
    ]
  }
}

function getCompressionOption(result: Result): EChartsOption {
  return {
    xAxis: {
      name: t('tools.brace_model.compression_x_axis'),
      max: 1.2 * result.delta_ub
    },
    yAxis: {
      name: t('tools.brace_model.compression_y_axis'),
      max: 1.2 * result.Nbe
    },
    series: [
      {
        type: 'line',
        data: [
          [0, 0],
          [result.delta_c, result.Nbe],
          [result.delta_ub, result.Nu_c]
        ],
        color: primaryColor.base
      },
      {
        type: 'line',
        data: [
          [result.delta_ub, result.Nu_c],
          [result.delta_ub, 0]
        ],
        color: primaryColor.base,
        lineStyle: {
          type: 'dashed'
        }
      }
    ]
  }
}
</script>

<template>
  <div class="tool-page">
    <disclaimer-component>
      <template #title>{{ $t('tools.common.disclaimer_title') }}</template>
      <i18n-t keypath="tools.common.disclaimer_text" tag="span" scope="global">
        <template #link>
          <a
            href="https://github.com/RESSLab-Team/resslab-hub/issues"
            target="_blank"
            rel="noopener noreferrer"
            >{{ $t('tools.common.disclaimer_link') }}</a
          >
        </template>
      </i18n-t>
    </disclaimer-component>
    <page-header :eyebrow="$t('tools.common.model_eyebrow')" :title="$t('tools.brace_model.title')">
      <template #actions><unit-toggle /></template>
      {{ $t('tools.brace_model.intro') }}
    </page-header>
    <div class="tool-shell">
      <div class="frag-a">
        <aside class="tool-panel">
          <div class="tool-card">
            <div class="tool-card-h with-info">
              {{ $t('tools.brace_model.cross_section_type') }}
              <info-tooltip>{{ $t('tools.brace_model.cross_section_type_help') }}</info-tooltip>
            </div>
            <tool-select
              :items="optionItems"
              :model-value="option"
              :placeholder="$t('tools.brace_model.select_option')"
              @update:model-value="option = ($event || 'wide-flange') as Option"
            />
          </div>

          <div class="tool-card">
            <div class="tool-card-h with-info">
              {{ $t('tools.brace_model.select_steel_profile') }}
              <info-tooltip>{{ $t('tools.brace_model.select_steel_profile_help') }}</info-tooltip>
            </div>
            <div class="tfield">
              <section-selector @update:section="onSectionChanged($event)" />
            </div>
            <div v-for="item in steelShapeDimensions" :key="item.key" class="tfield">
              <tool-slider
                v-model="variables[item.key]"
                :disabled="!!section"
                :label="item.text"
                :max="item.max"
                :min="item.min"
                :unit="item.unit"
              />
            </div>
          </div>

          <div class="tool-card">
            <div class="tool-card-h with-info">
              {{ $t('tools.brace_model.steel_type') }}
              <info-tooltip>{{ $t('tools.brace_model.steel_type_help') }}</info-tooltip>
            </div>
            <div class="tfield">
              <tool-select
                :items="steelTypeItems"
                :model-value="steelType"
                :placeholder="$t('tools.brace_model.select_steel_type')"
                @update:model-value="steelType = ($event || undefined) as SteelType | undefined"
              />
            </div>
            <div v-for="item in steelTypeVariables" :key="item.key" class="tfield">
              <tool-slider
                v-model="variables[item.key]"
                :disabled="!!steelType"
                :label="item.text"
                :max="item.max"
                :min="item.min"
                :unit="item.unit"
              />
            </div>
          </div>

          <div class="tool-card">
            <div class="tool-card-h with-info">
              {{ $t('tools.brace_model.associated_member_lengths') }}
              <info-tooltip>{{
                $t('tools.brace_model.associated_member_lengths_help')
              }}</info-tooltip>
            </div>
            <div v-for="item in additionalParameterVariables" :key="item.key" class="tfield">
              <tool-slider
                v-model="variables[item.key]"
                :label="item.text"
                :max="item.max"
                :min="item.min"
                :unit="item.unit"
              />
            </div>
          </div>
        </aside>

        <section class="tool-chart-col">
          <figure class="tool-schematic is-small">
            <img
              :alt="$t('tools.brace_model.schematic_alt')"
              :src="publicPath + 'img/brace/I_shaped_Bracing.png'"
            />
          </figure>
          <div class="tool-chart-grid">
            <div class="mat-focus">
              <h2 class="tool-chart-h">{{ $t('tools.brace_model.tension') }}</h2>
              <unit-chart :option="getTensionOption(result)" />
            </div>
            <div class="mat-focus">
              <h2 class="tool-chart-h">{{ $t('tools.brace_model.compression') }}</h2>
              <unit-chart :option="getCompressionOption(result)" />
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>
