<script setup lang="ts">
import UnitChart from '@/components/commons/charts/UnitChart.vue'
import InfoTooltip from '@/components/commons/InfoTooltip.vue'
import SectionSelector from '@/components/commons/SectionSelector.vue'
import ToolSlider from '@/components/commons/tools/ToolSlider.vue'
import type { Variable } from '@/utils/model'
import ToolShell from '@/components/commons/ToolShell.vue'
import UnitTableRow, { type UnitTableRowData } from '@/components/commons/UnitTableRow.vue'
import UnitToggle from '@/components/commons/UnitToggle.vue'
import { publicPath, type Section, type HSSSection } from '@/utils/common'
import type { Point } from '@/utils/model'
import { primaryColor, secondaryColor } from '@/utils/vuetify'
import type { EChartsOption } from 'echarts'
import { omit } from 'lodash'
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })

interface Result {
  ke: number
  my: number
  mc: number
  mRes: number
  thetaP: number
  thetaPc: number
  thetaUlt: number
  lamdbaS?: number
  lamdbaC?: number
  points: Point[]
}

interface Envelope {
  thetaY: number
  mc: number
  thetaP: number
  thetaPc: number
  res: number
  mRes: number
  thetaUlt: number
  alpha: number
  alphaPc: number
}

interface Backbone extends Envelope {
  a: number
  lambdaS: number
  lambdaC: number
}

const steelShapeDimensions: Variable<keyof Variables>[] = [
  {
    key: 'b',
    text: 'b',
    unit: 'mm',
    min: 200,
    max: 1000
  },
  {
    key: 'h',
    text: 'h',
    unit: 'mm',
    min: 200,
    max: 1000
  },
  {
    key: 't',
    text: 't',
    unit: 'mm',
    min: 5,
    max: 100
  }
]
const memberProperties: Variable<keyof Variables>[] = [
  {
    key: 'pgPye',
    text: 'P<sub>g</sub>/P<sub>ye</sub>',
    min: 0,
    max: 1
  },
  {
    key: 'l',
    text: 'L',
    unit: 'mm',
    min: 3000,
    max: 8000
  },
  {
    key: 'fy',
    text: 'F<sub>y</sub>',
    unit: 'MPa',
    min: 250,
    max: 500
  }
]
const rows: UnitTableRowData[] = [
  {
    key: 'ke',
    text: 'K<sub>e</sub>',
    unit: '<sup>kN⋅mm</sup>/<sub>rad</sub>',
    fractionDigit: 0
  },
  {
    key: 'my',
    text: 'M<sub>y</sub>',
    unit: 'kN⋅mm',
    fractionDigit: 0
  },
  {
    key: 'mc',
    text: 'M<sub>c</sub>',
    unit: 'kN⋅mm',
    fractionDigit: 0
  },
  {
    key: 'mRes',
    text: 'M<sub>r</sub>',
    unit: 'kN⋅mm',
    fractionDigit: 0
  },
  {
    key: 'thetaP',
    text: '&theta;<sub>p</sub>',
    unit: 'rad',
    fractionDigit: 3
  },
  {
    key: 'thetaPc',
    text: '&theta;<sub>pc</sub>',
    unit: 'rad',
    fractionDigit: 3
  },
  {
    key: 'thetaUlt',
    text: '&theta;<sub>u</sub>',
    unit: 'rad',
    fractionDigit: 3
  },
  {
    key: 'lamdbaS',
    text: '&Lambda;<sub>S</sub>',
    unit: 'rad',
    fractionDigit: 3
  },
  {
    key: 'lamdbaC',
    text: '&Lambda;<sub>C</sub>',
    unit: 'rad',
    fractionDigit: 3
  }
]

const section = ref<HSSSection>()

const e = 205
interface Variables {
  b: number
  h: number
  t: number
  pgPye: number
  l: number
  fy: number
}
const variables = reactive<Variables>({
  b: 300,
  h: 300,
  t: 10,
  pgPye: 0.2,
  l: 5000,
  fy: 380
})

const vars = computed(() => {
  const { b, h, t, pgPye, l, fy } = variables

  let ix: number
  let zx: number

  if (section.value) {
    ix = section.value.iy
    zx = section.value.zy
  } else {
    const b1 = h - 2 * t,
      b2 = b - 2 * t

    // formulas comes from https://www.engineersedge.com/calculators/section_square_case_10.htm

    //  moment of inertia of a hollow square section
    ix = (b * h ** 3 - b2 * b1 ** 3) / 12
    // sections modulus
    zx = (b * h ** 2 - b2 * b1 ** 2) / 4
  }

  // total member response
  // shear modulus
  // const g = e / (2 * (1 + 0.3))
  // sgear area of hss cross section
  // const aw = 2 * b * t

  // flexural stiffness (member in double curvature)
  const ke = (6 * e * ix) / l

  const my =
    pgPye < 0.2
      ? 1.2 * zx * (fy / 1000) * (1 - pgPye / 2)
      : 1.2 * zx * (fy / 1000) * (9 / 8) * (1 - pgPye)

  return {
    ix,
    ke,
    zx,
    my
  }
})

const backbone = computed<Backbone>(() => {
  const { t, h, pgPye, fy } = variables
  const { ke, my } = vars.value

  // capping to yield ratio
  const a = 1.2

  // Capping strength
  const mc = a * my

  // Residual strength
  const res = 0.25
  const mRes = res * my

  // Yield rotation of the member
  const thetaY = my / ke

  // plastic rotation
  const thetaP = Math.min(
    0.2,
    0.001 * Math.pow(h / t, -2.32) * Math.pow(e / (fy / 1000), 1.73) * Math.pow(1 - pgPye, 0.87)
  )

  // post-capping plastic rotation
  const thetaPc = Math.min(
    0.3,
    0.0054 * Math.pow(h / t, -1.22) * Math.pow(e / (fy / 1000), 1.25) * Math.pow(1 - pgPye, 3.31)
  )

  // Ultimate rotation
  const thetaUlt = 0.25

  // Post-yielding stiffness of the member
  const alpha = (mc - my) / thetaP / ke

  // Post-peak stiffness of the member
  const alphaPc = (0.0 - mc) / (ke * thetaPc)

  // Reference Cumulative Plastic Rotation
  const lambdaS = Math.min(3.0, 951.0 * Math.pow(h / t, -2.2) * Math.pow(1 - pgPye, 3.02))
  const lambdaC = Math.min(3.0, 1791.0 * Math.pow(h / t, -2.31) * Math.pow(1 - pgPye, 4.91))

  return {
    thetaY,
    a,
    mc,
    thetaP,
    thetaPc,
    res,
    mRes,
    thetaUlt,
    alpha,
    alphaPc,
    lambdaS,
    lambdaC
  }
})
const envelope = computed<Envelope>(() => {
  const { h, t, pgPye } = variables
  const { ke, my } = vars.value
  // capping to yield ratio

  const a = 1.15
  // Capping strength
  const mc = a * my

  // Residual strength
  const res = 0.25
  const mRes = res * my

  // Yield rotation of the member
  const thetaY = my / ke

  // plastic rotation
  const thetaP = Math.min(0.1, 0.71 * Math.pow(h / t, -0.98) * Math.pow(1 - pgPye, 1.81))

  // post-capping plastic rotation
  const thetaPc = Math.min(0.1, 0.44 * Math.pow(h / t, -0.74) * Math.pow(1 - pgPye, 2.8))

  // Ultimate rotation
  const thetaUlt =
    thetaY + Math.min(0.15, 0.27 * Math.pow(h / t, -0.51) * Math.pow(1 - pgPye, 1.45))

  // Post-yielding stiffness of the member
  const alpha = (mc - my) / thetaP / ke

  // Post-peak stiffness of the member
  const alphaPc = -mc / (ke * thetaPc)

  return {
    thetaY,
    mc,
    thetaP,
    thetaPc,
    res,
    mRes,
    thetaUlt,
    alpha,
    alphaPc
  }
})
const backboneResult = computed<Result>(() => getResult(backbone.value))
const envelopeResult = computed<Result>(() => getResult(envelope.value))

function onSectionChanged(value?: HSSSection | Section): void {
  const hssValue = value as HSSSection //This come from putting source="hss" for section-selector
  section.value = hssValue
  if (hssValue) {
    variables.b = hssValue.b
    variables.t = hssValue.t
    variables.h = hssValue.h
  }
}

function getPoints(output: Envelope | Backbone): Point[] {
  const { ke, my } = vars.value

  const p1: Point = [0, 0]
  const p2: Point = [output.thetaY, my]
  const p3: Point = [p2[0] + output.thetaP, output.mc]
  const p4: Point = [p3[0] + (output.mc - output.mRes) / (-output.alphaPc * ke), output.mRes]
  if (p4[0] < output.thetaUlt) {
    const p5: Point = [output.thetaUlt, output.mRes]
    const p6: Point = [p5[0], 0]
    return [p1, p2, p3, p4, p5, p6]
  } else if (p3[0] < output.thetaUlt) {
    // && output.thetaUlt <= p4[0]
    const p5: Point = [
      output.thetaUlt,
      output.mc + output.alphaPc * ke * Math.abs(p3[0] - output.thetaUlt)
    ]
    const p6: Point = [p5[0], 0]
    return [p1, p2, p3, p5, p6]
  } else if (p2[0] < output.thetaUlt) {
    // && output.thetaUlt <= p3[0]
    const p5: Point = [output.thetaUlt, my + output.alpha * ke * (output.thetaUlt - output.thetaY)]
    const p6: Point = [p5[0], 0]
    return [p1, p2, p5, p6]
  } else {
    const p5: Point = [output.thetaUlt, ke * output.thetaUlt]
    const p6: Point = [p5[0], 0]
    return [p1, p5, p6]
  }
}

function getResult(output: Envelope | Backbone): Result {
  const { ke, my } = vars.value
  return {
    ke: ke,
    my: my,
    lamdbaS: (output as Backbone).lambdaS,
    lamdbaC: (output as Backbone).lambdaC,
    ...output,
    points: getPoints(output)
  }
}

function getOption(backbone: Result, envelope: Result): EChartsOption {
  return {
    xAxis: {
      name: t('tools.hss_model.chart_x_axis')
    },
    yAxis: {
      name: t('tools.hss_model.chart_y_axis')
    },
    series: [
      {
        type: 'line',
        name: t('tools.hss_model.series_monotonic_backbone'),
        data: backbone.points,
        color: primaryColor.base
      },
      {
        type: 'line',
        name: t('tools.hss_model.series_first_cycle_envelope'),
        data: envelope.points,
        color: secondaryColor.base
      }
    ]
  }
}

function getTableColumns(...results: Result[]): Record<string, number | undefined>[] {
  return results.map((result) => omit(result, 'points'))
}

const paramCount = computed(() => steelShapeDimensions.length + memberProperties.length)

defineExpose({ vars, backbone, envelope })
</script>

<template>
  <tool-shell
    :eyebrow="$t('tools.common.model_eyebrow')"
    :title="$t('tools.hss_model.title')"
    :param-count="paramCount"
  >
    <template #actions><unit-toggle /></template>
    <template #intro>
      <i18n-t keypath="tools.hss_model.intro" tag="span" scope="global">
        <template #link>
          <a href="" target="_blank">{{ $t('tools.hss_model.intro_link') }}</a>
        </template>
      </i18n-t>
    </template>

    <template #rail>
      <div class="tool-card">
        <div class="tool-card-h with-info">
          {{ $t('tools.hss_model.select_hss_profile') }}
          <info-tooltip>{{ $t('tools.hss_model.select_hss_profile_help') }}</info-tooltip>
        </div>
        <div class="tfield">
          <section-selector source="hss" @update:section="onSectionChanged($event)" />
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
          {{ $t('tools.hss_model.member_loading_properties') }}
          <info-tooltip>{{ $t('tools.hss_model.member_loading_properties_help') }}</info-tooltip>
        </div>
        <div v-for="item in memberProperties" :key="item.key" class="tfield">
          <tool-slider
            v-model="variables[item.key]"
            :label="item.text"
            :max="item.max"
            :min="item.min"
            :unit="item.unit"
          />
        </div>
      </div>
    </template>

    <template #stage>
      <div class="st-block st-chart">
        <div class="chart-cap">
          <h2 class="chart-h">{{ $t('tools.hss_model.backbone_curve') }}</h2>
        </div>
        <div class="tchart h-chart">
          <unit-chart
            fill
            :option="getOption(backboneResult, envelopeResult)"
            x-unit="rad"
            y-unit="kN⋅mm"
          />
        </div>
      </div>

      <div class="st-block st-table">
        <div class="tool-card-h with-info">
          {{ $t('tools.hss_model.predictive_model_columns') }}
          <info-tooltip>{{ $t('tools.hss_model.predictive_model_columns_help') }}</info-tooltip>
        </div>
        <v-table density="compact">
          <thead>
            <tr>
              <th class="text-center">{{ $t('tools.hss_model.table_parameter') }}</th>
              <th class="text-center">{{ $t('tools.hss_model.table_unit') }}</th>
              <th class="text-center">{{ $t('tools.hss_model.table_monotonic_backbone') }}</th>
              <th class="text-center">{{ $t('tools.hss_model.table_first_cycle_envelope') }}</th>
            </tr>
          </thead>
          <tbody>
            <unit-table-row
              v-for="item in rows"
              :key="item.key"
              :field="item.key"
              :text="item.text"
              :unit="item.unit"
              :fraction-digit="item.fractionDigit"
              :columns="getTableColumns(backboneResult, envelopeResult)"
            />
          </tbody>
        </v-table>
      </div>

      <div class="st-block st-schem">
        <figure class="tool-schematic">
          <img
            :alt="$t('tools.hss_model.schematic_alt')"
            :src="publicPath + 'img/hss/component.png'"
          />
        </figure>
      </div>
    </template>
  </tool-shell>
</template>
