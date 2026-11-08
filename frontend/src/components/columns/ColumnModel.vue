<script setup lang="ts">
// Computations from https://github.com/RESSLab-Team/resslab-hub-scripts/tree/main/steel_columns
import UnitChart from '@/components/commons/charts/UnitChart.vue'
import InfoTooltip from '@/components/commons/InfoTooltip.vue'
import SectionSelector from '@/components/commons/SectionSelector.vue'
import ToolSlider from '@/components/commons/tools/ToolSlider.vue'
import type { Variable } from '@/utils/model'
import ToolShell from '@/components/commons/ToolShell.vue'
import UnitTableRow, { type UnitTableRowData } from '@/components/commons/UnitTableRow.vue'
import UnitToggle from '@/components/commons/UnitToggle.vue'
import { publicPath, type Section } from '@/utils/common'
import type { Point } from '@/utils/model'
import { primaryColor, secondaryColor } from '@/utils/vuetify'
import type { EChartsOption } from 'echarts'
import { clamp, omit } from 'lodash'
import { computed, reactive, ref, watch } from 'vue'
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
  lamdba?: number
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
  lambda: number
}

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
const memberProperties = ref<Variable<keyof Variables>[]>([
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
    key: 'lb',
    text: 'L<sub>b</sub>',
    unit: 'mm',
    min: 3000,
    // Max value should be the value of L
    max: 12000
  },
  {
    key: 'fy',
    text: 'F<sub>y</sub>',
    unit: 'MPa',
    min: 250,
    max: 500
  }
])

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
    key: 'lamdba',
    text: '&Lambda;',
    unit: 'rad',
    fractionDigit: 3
  }
]

const section = ref<Section>()

const e = 205
interface Variables {
  bf: number
  d: number
  tf: number
  tw: number
  pgPye: number
  l: number
  lb: number
  fy: number
}
const variables = reactive<Variables>({
  bf: 100,
  d: 100,
  tf: 5,
  tw: 5,
  pgPye: 0.2,
  l: 5000,
  lb: 5000,
  fy: 380
})

watch(
  () => variables.l,
  (value) => {
    memberProperties.value[2].max = value
    variables.lb = Math.min(variables.lb, value)
  },
  { immediate: true }
)

const vars = computed(() => {
  const { bf, d, tf, tw, pgPye, l, fy } = variables

  let h: number
  let ix: number
  let ry: number
  let zx: number
  if (section.value) {
    h = section.value.h
    ix = section.value.ix
    ry = section.value.ry
    zx = section.value.zx
  } else {
    h = d - 2 * tf
    ix =
      (Math.pow(d - 2 * tf, 3) * tw) / 12 +
      2 * bf * tf * (Math.pow(tf, 2) / 12 + Math.pow((d - tf) / 2, 2))
    ry = Math.sqrt(
      ((2 * tf * Math.pow(bf, 3)) / 12 + ((d - 2 * tf) * Math.pow(tw, 3)) / 12) /
        (2 * tf * bf + (d - 2 * tf) * tw)
    )
    zx = 2 * (bf * tf * ((d - tf) / 2) + (Math.pow(d - 2 * tf, 2) * tw) / 8)
  }

  const ke = (6 * e * ix) / l
  const my =
    pgPye < 0.2
      ? 1.15 * zx * (fy / 1000) * (1 - pgPye / 2)
      : 1.15 * zx * (fy / 1000) * (9 / 8) * (1 - pgPye)
  return {
    h,
    ix,
    ry,
    ke,
    zx,
    my
  }
})

const backbone = computed<Backbone>(() => {
  const { tw, pgPye, lb } = variables
  const { h, ry, ke, my } = vars.value

  const a = clamp(
    12.5 * Math.pow(h / tw, -0.2) * Math.pow(lb / ry, -0.4) * Math.pow(1 - pgPye, 0.4),
    1,
    1.3
  )
  const mc = a * my
  const res = 0.5 - 0.4 * pgPye
  const mRes = res * my
  const thetaY = my / ke
  const thetaP = Math.min(
    0.2,
    294 * Math.pow(h / tw, -1.7) * Math.pow(lb / ry, -0.7) * Math.pow(1 - pgPye, 1.6)
  )
  const thetaPc = Math.min(
    0.3,
    90 * Math.pow(h / tw, -0.8) * Math.pow(lb / ry, -0.8) * Math.pow(1 - pgPye, 2.5)
  )
  const thetaUlt = 0.15
  const alpha = (mc - my) / thetaP / ke
  const alphaPc = -mc / (ke * thetaPc)
  const lambda =
    pgPye <= 0.35
      ? Math.min(
          3.0,
          25000 * Math.pow(h / tw, -2.14) * Math.pow(lb / ry, -0.53) * Math.pow(1 - pgPye, 4.92)
        )
      : Math.min(
          3.0,
          268000 * Math.pow(h / tw, -2.3) * Math.pow(lb / ry, -1.3) * Math.pow(1 - pgPye, 1.19)
        )
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
    lambda
  }
})
const envelope = computed<Envelope>(() => {
  const { tw, pgPye, lb } = variables
  const { h, ry, ke, my } = vars.value

  const a = clamp(
    9.5 * Math.pow(h / tw, -0.4) * Math.pow(lb / ry, -0.16) * Math.pow(1 - pgPye, 0.2),
    1,
    1.2
  )
  const mc = a * my
  const res = 0.4 - 0.4 * pgPye
  const mRes = res * my
  const thetaY = my / ke
  const thetaP = Math.min(
    0.1,
    15 * Math.pow(h / tw, -1.6) * Math.pow(lb / ry, -0.3) * Math.pow(1 - pgPye, 2.3)
  )
  const thetaPc = Math.min(
    0.1,
    14 * Math.pow(h / tw, -0.8) * Math.pow(lb / ry, -0.5) * Math.pow(1 - pgPye, 3.2)
  )
  const thetaUlt = 0.08 * (1 - 0.6 * pgPye)
  const alpha = (mc - my) / thetaP / ke
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

function onSectionChanged(value?: Section): void {
  section.value = value
  if (value) {
    variables.bf = value.bf
    variables.d = value.d
    variables.tf = value.tf
    variables.tw = value.tw
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
      output.mc + output.alphaPc * ke * Math.abs(output.thetaPc - output.thetaUlt)
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
    lamdba: (output as Backbone).lambda,
    ...output,
    points: getPoints(output)
  }
}

// Computed rather than built inline in the template: a template call would mint a
// fresh option object on every re-render and vue-echarts would push each one
// through `setOption`. Series carry stable ids so a parameter change merges into
// the rendered series instead of replacing them.
const chartOption = computed<EChartsOption>(() => ({
  xAxis: {
    name: t('tools.column_model.chart_x_axis')
  },
  yAxis: {
    name: t('tools.column_model.chart_y_axis')
  },
  series: [
    {
      id: 'backbone',
      type: 'line',
      name: t('tools.column_model.series_monotonic_backbone'),
      data: backboneResult.value.points,
      color: primaryColor.base
    },
    {
      id: 'envelope',
      type: 'line',
      name: t('tools.column_model.series_first_cycle_envelope'),
      data: envelopeResult.value.points,
      color: secondaryColor.base
    }
  ]
}))

const tableColumns = computed<Record<string, number | undefined>[]>(() =>
  [backboneResult.value, envelopeResult.value].map((result) => omit(result, 'points'))
)

const paramCount = computed(() => steelShapeDimensions.length + memberProperties.value.length)

defineExpose({ vars, backbone, envelope, variables, onSectionChanged })
</script>

<template>
  <tool-shell
    :eyebrow="$t('tools.common.model_eyebrow')"
    :title="$t('tools.column_model.title')"
    :param-count="paramCount"
  >
    <template #actions><unit-toggle /></template>
    <template #intro>
      <i18n-t keypath="tools.column_model.intro" tag="span" scope="global">
        <template #link>
          <a href="" target="_blank" rel="noopener noreferrer">{{
            $t('tools.column_model.intro_link')
          }}</a>
        </template>
      </i18n-t>
    </template>

    <template #rail>
      <div class="tool-card">
        <div class="tool-card-h with-info">
          {{ $t('tools.column_model.select_steel_profile') }}
          <info-tooltip>{{ $t('tools.column_model.select_steel_profile_help') }}</info-tooltip>
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
          {{ $t('tools.column_model.member_loading_properties') }}
          <info-tooltip>{{ $t('tools.column_model.member_loading_properties_help') }}</info-tooltip>
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
          <div class="chart-cap-t">
            <h2 class="chart-h">{{ $t('tools.column_model.backbone_curve') }}</h2>
            <p class="chart-sub">{{ $t('tools.column_model.backbone_curve_sub') }}</p>
          </div>
        </div>
        <div class="tchart h-chart">
          <unit-chart fill :option="chartOption" x-unit="rad" y-unit="kN⋅mm" />
        </div>
      </div>

      <div class="st-block st-table">
        <div class="tool-card-h with-info">
          {{ $t('tools.column_model.predictive_model') }}
          <info-tooltip>{{ $t('tools.column_model.predictive_model_help') }}</info-tooltip>
        </div>
        <v-table density="compact">
          <thead>
            <tr>
              <th class="text-center">{{ $t('tools.column_model.table_parameter') }}</th>
              <th class="text-center">{{ $t('tools.column_model.table_unit') }}</th>
              <th class="text-center">{{ $t('tools.column_model.table_monotonic_backbone') }}</th>
              <th class="text-center">{{ $t('tools.column_model.table_first_cycle_envelope') }}</th>
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
              :columns="tableColumns"
            />
          </tbody>
        </v-table>
      </div>

      <div class="st-block st-schem">
        <figure class="tool-schematic">
          <img
            :alt="$t('tools.column_model.schematic_alt')"
            :src="publicPath + 'img/column/component.png'"
          />
          <figcaption>{{ $t('tools.column_model.figcaption') }}</figcaption>
        </figure>
      </div>
    </template>
  </tool-shell>
</template>
