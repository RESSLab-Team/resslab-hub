<script setup lang="ts">
// Computations from https://github.com/RESSLab-Team/resslab-hub-scripts/tree/main/steel_beams
import UnitChart from '@/components/commons/charts/UnitChart.vue'
import InfoTooltip from '@/components/commons/InfoTooltip.vue'
import SectionSelector from '@/components/commons/SectionSelector.vue'
import UnitSlider, { type Variable } from '@/components/commons/sliders/UnitSlider.vue'
import TitleRow from '@/components/commons/TitleRow.vue'
import UnitTableRow, { type UnitTableRowData } from '@/components/commons/UnitTableRow.vue'
import { publicPath, type Section } from '@/utils/common'
import { variableBind, type Point } from '@/utils/model'
import { primaryColor, secondaryColor } from '@/utils/vuetify'
import type { EChartsOption } from 'echarts'
import { clamp, omit } from 'lodash'
import { computed, reactive, ref } from 'vue'

interface Variables {
  bf: number
  d: number
  tf: number
  tw: number
  rbsReduction: number
  l: number
  lb: number
  fy: number
}
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
  my: number
  thetaY: number
  mc: number
  thetaP: number
  thetaPc: number
  res: number
  mRes: number
  thetaUlt: number
  alpha: number
  alphaPc: number
  zx: number
  lRbs?: number
  // For debugging
  zRbs?: number
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
const memberProperties: Variable<keyof Variables>[] = [
  {
    key: 'rbsReduction',
    text: 'RBS flange reduction',
    min: 0,
    max: 0.5
  },
  {
    key: 'l',
    text: 'L',
    unit: 'mm',
    min: 1000,
    max: 12000
  },
  {
    key: 'lb',
    text: 'L<sub>b</sub>',
    unit: 'mm',
    min: 1000,
    max: 12000
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
    key: 'lamdba',
    text: '&Lambda;',
    unit: 'rad',
    fractionDigit: 3
  }
]

const section = ref<Section>()

const e = 205

const variables = reactive<Variables>({
  bf: 100,
  d: 100,
  tf: 5,
  tw: 5,
  rbsReduction: 0.5,
  l: 8000,
  lb: 4000,
  fy: 380
})

const vars = computed(() => {
  const { bf, d, tf, tw, l } = variables

  let h: number
  let ix: number
  let ry: number
  if (section.value) {
    h = section.value.h
    ix = section.value.ix
    ry = section.value.ry
  } else {
    h = d - 2 * tf
    ix =
      (Math.pow(d - 2 * tf, 3) * tw) / 12 +
      2 * bf * tf * (Math.pow(tf, 2) / 12 + Math.pow((d - tf) / 2, 2))
    ry = Math.sqrt(
      ((tf * Math.pow(bf, 3)) / 12 + ((d - 2 * tf) * Math.pow(tw, 3)) / 12) /
        (2 * tf * bf + (d - 2 * tf) * tw)
    )
  }
  const ke = (6 * e * ix) / l
  const le = l / 2
  return {
    h,
    ix,
    ry,
    ke,
    le
  }
})

const rbs = computed<{
  zx: number
  lRbs: number
  zRbs: number
  my: number
}>(() => {
  const { bf, d, tf, rbsReduction, fy } = variables

  const _a = 0.625 * bf
  const _b = 0.75 * d
  const _c = rbsReduction * bf
  const zx = getZx(true)
  const lRbs = _a + 0.5 * _b
  const zRbs = zx - _c * tf * (d - tf)

  const my = 1.06 * zRbs * (fy / 1000)
  return {
    zx,
    lRbs,
    zRbs,
    my
  }
})
const backboneRbs = computed(() => {
  const { bf, d, tf, tw, lb, fy } = variables
  const { h, ry, ke, le } = vars.value
  const { zx, lRbs, zRbs, my } = rbs.value

  const a = 1.09
  const mc = a * my
  const res = 0.4
  const mRes = res * my

  const thetaY = my / ke
  const thetaP =
    0.19 *
    Math.pow(h / tw, -0.314) *
    Math.pow(bf / 2 / tf, -0.1) *
    Math.pow(lb / ry, -0.185) *
    Math.pow((le - lRbs) / d, 0.113) *
    Math.pow(d / 533, -0.76) *
    Math.pow(fy / 355, -0.07)
  const thetaPc =
    9.52 *
    Math.pow(h / tw, -0.513) *
    Math.pow(bf / 2 / tf, -0.863) *
    Math.pow(lb / ry, -0.108) *
    Math.pow(fy / 355, -0.36)
  const thetaUlt = 0.2
  const alpha = ((mc - my) / thetaP / ke) * (le / (le - lRbs))
  const alphaPc = (-mc / (ke * thetaPc)) * (le / (le - lRbs))
  const lambda = clamp(
    585 *
      Math.pow(h / tw, -1.14) *
      Math.pow(bf / 2 / tf, -0.632) *
      Math.pow(lb / ry, -0.205) *
      Math.pow(fy / 355, -0.391),
    3.0
  )
  return {
    my,
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
    zx,
    lRbs,
    lambda,
    zRbs
  }
})
const envelopeRbs = computed<Envelope>(() => {
  const { bf, d, tf, tw, lb, fy } = variables
  const { h, ry, ke, le } = vars.value
  const { zx, lRbs, zRbs, my } = rbs.value

  const res = 0.3
  const mRes = res * my

  const thetaY = my / ke
  const thetaP =
    0.25 *
    Math.pow(h / tw, -0.5) *
    Math.pow(bf / 2 / tf, -0.7) *
    Math.pow(lb / ry, -0.5) *
    Math.pow((le - lRbs) / d, 0.8) *
    Math.pow(e / fy, 0.23)
  const thetaPc = clamp(
    2.5 *
      Math.pow(h / tw, -1.1) *
      Math.pow(bf / 2 / tf, -0.1) *
      Math.pow(lb / ry, -0.1) *
      Math.pow(e / fy, 0.09),
    0.05
  )
  const thetaUlt = 0.08
  const alpha = 0.03
  const mc = my + alpha * ke * thetaP

  const alphaPc = (-mc / (ke * thetaPc)) * (le / (le - lRbs))
  return {
    my,
    thetaY,
    mc,
    thetaP,
    thetaPc,
    res,
    mRes,
    thetaUlt,
    alpha,
    alphaPc,
    zx,
    lRbs,
    zRbs
  }
})
const nonRbs = computed<{
  zx: number
  my: number
}>(() => {
  const { fy } = variables

  const zx = getZx(false)
  const my = 1.17 * zx * (fy / 1000)
  return {
    zx,
    my
  }
})
const backboneNonRbs = computed<Backbone>(() => {
  const { bf, d, tf, tw, lb, fy } = variables
  const { h, ry, ke, le } = vars.value
  const { zx, my } = nonRbs.value

  const a = 1.11
  const mc = a * my
  const res = 0.4
  const mRes = res * my

  const thetaY = my / ke

  let thetaP
  let thetaPc
  let lambda
  if (d <= 533) {
    thetaP =
      0.0865 *
      Math.pow(h / tw, -0.365) *
      Math.pow(bf / 2 / tf, -0.14) *
      Math.pow(le / d, 0.34) *
      Math.pow(d / 533, -0.721) *
      Math.pow(fy / 355, -0.23)
    thetaPc =
      5.63 *
      Math.pow(h / tw, -0.565) *
      Math.pow(bf / 2 / tf, -0.8) *
      Math.pow(d / 533, -0.28) *
      Math.pow(fy / 355, -0.43)
    lambda = clamp(
      536 *
        Math.pow(h / tw, -1.26) *
        Math.pow(bf / 2 / tf, -0.525) *
        Math.pow(lb / ry, -0.13) *
        Math.pow(fy / 355, -0.291),
      3.0
    )
  } else {
    thetaP =
      0.318 *
      Math.pow(h / tw, -0.55) *
      Math.pow(bf / 2 / tf, -0.345) *
      Math.pow(lb / ry, -0.023) *
      Math.pow(le / d, 0.09) *
      Math.pow(d / 533, -0.33) *
      Math.pow(fy / 355, -0.13)

    thetaPc =
      7.5 *
      Math.pow(h / tw, -0.61) *
      Math.pow(bf / 2 / tf, -0.71) *
      Math.pow(lb / ry, -0.11) *
      Math.pow(d / 533, -0.161) *
      Math.pow(fy / 355, -0.32)
    lambda = clamp(
      585 *
        Math.pow(h / tw, -1.14) *
        Math.pow(bf / 2 / tf, -0.632) *
        Math.pow(lb / ry, -0.205) *
        Math.pow(fy / 355, -0.391),
      3.0
    )
  }
  const thetaUlt = 0.2
  const alpha = (mc - my) / thetaP / ke
  const alphaPc = -mc / (ke * thetaPc)
  return {
    my,
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
    zx,
    lambda
  }
})
const envelopeNonRbs = computed<Envelope>(() => {
  const { bf, d, tf, tw, lb, fy } = variables
  const { h, ry, ke, le } = vars.value
  const { zx, my } = nonRbs.value
  const res = 0.3
  const mRes = res * my
  const thetaY = my / ke

  const thetaP =
    0.5 *
    Math.pow(h / tw, -0.9) *
    Math.pow(bf / 2 / tf, -1.1) *
    Math.pow(lb / ry, -0.2) *
    Math.pow(le / d, 1.1) *
    Math.pow(e / fy, 0.2)
  const thetaPc = clamp(
    6.4 *
      Math.pow(h / tw, -0.9) *
      Math.pow(bf / 2 / tf, -0.2) *
      Math.pow(lb / ry, -0.5) *
      Math.pow(e / fy, 0.1),
    0.05
  )
  const thetaUlt = 0.08
  const alpha = 0.03
  const mc = my + alpha * ke * thetaP
  const alphaPc = (0.0 - mc) / (ke * thetaPc)
  return {
    my,
    thetaY,
    mc,
    thetaP,
    thetaPc,
    res,
    mRes,
    thetaUlt,
    alpha,
    alphaPc,
    zx
  }
})
const backboneWithRbs = computed<Result>(() => getResult(backboneRbs.value))
const backboneWithoutRbs = computed<Result>(() => getResult(backboneNonRbs.value))
const envelopeWithRbs = computed<Result>(() => getResult(envelopeRbs.value))
const envelopeWithoutRbs = computed<Result>(() => getResult(envelopeNonRbs.value))

function getZx(rbs: boolean): number {
  const { bf, d, tf, tw, rbsReduction } = variables

  if (section.value) {
    return section.value.zx
  }
  const n = rbs ? rbsReduction : 1
  return 2 * (n * bf * tf * ((d - tf) / 2) + (Math.pow(d - 2 * tf, 2) * tw) / 4)
}

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
  const { ke } = vars.value

  const p1: Point = [0, 0]
  const p2: Point = [output.thetaY, output.my]
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
    const p5: Point = [
      output.thetaUlt,
      output.my + output.alpha * ke * (output.thetaUlt - output.thetaY)
    ]
    const p6: Point = [p5[0], 0]
    return [p1, p2, p5, p6]
  } else {
    const p5: Point = [output.thetaUlt, ke * output.thetaUlt]
    const p6: Point = [p5[0], 0]
    return [p1, p5, p6]
  }
}

function getResult(output: Envelope | Backbone): Result {
  const { ke } = vars.value
  return {
    ke: ke,
    lamdba: (output as Backbone).lambda,
    ...output,
    points: getPoints(output)
  }
}

function option(backbone: Result, envelope: Result): EChartsOption {
  return {
    xAxis: {
      name: 'Chord Rotation, θ'
    },
    yAxis: {
      name: 'Moment, M'
    },
    series: [
      {
        type: 'line',
        name: 'Monotonic Backbone',
        data: backbone.points,
        color: primaryColor.base
      },
      {
        type: 'line',
        name: 'First-Cycle Envelope',
        data: envelope.points,
        color: secondaryColor.base
      }
    ]
  }
}

defineExpose({ vars, backboneRbs, backboneNonRbs, envelopeRbs, envelopeNonRbs })
</script>

<template>
  <v-row>
    <v-col cols="12">
      <title-row>
        <h1>Backbone Curve Plotter for Steel Components</h1>
        <p>
          Construct the backbone curve of beams with RBS and beams other-than-RBS. For further
          information refer to
          <a
            href="http://ascelibrary.org/doi/abs/10.1061/(ASCE)ST.1943-541X.0000376"
            target="_blank"
          >
            Lignos and Krawinkler (2011)
          </a>
        </p>
      </title-row>
    </v-col>
    <v-col cols="6">
      <v-row>
        <v-col>
          <v-card>
            <v-card-title>
              Select Steel Profile
              <info-tooltip>
                Here, you may choose to either select a W-Shape from the AISC database or input your
                own dimensions using the sliders below
              </info-tooltip>
            </v-card-title>
            <v-card-text>
              <section-selector @update:section="onSectionChanged($event)" />
              <v-row>
                <v-col v-for="item in steelShapeDimensions" :key="item.key" v-bind="variableBind">
                  <unit-slider
                    v-model="variables[item.key]"
                    :disabled="!!section"
                    :label="item.text"
                    :max="item.max"
                    :min="item.min"
                    :unit="item.unit"
                  />
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <v-card>
            <v-card-title>
              Specify Member Properties
              <info-tooltip>
                Here you need to specify the beam full length (L), the beam unbraced length
                (L<sub>b</sub>), which is defined as the distance from the column face to the
                nearest lateral brace, the expected yield stress, F<sub>y</sub> of the steel
                material, the capping-to-yield ratio <sup>Mc</sup>/<sub>My</sub>, the expected
                residual strength ratio, K, and the ultimate rotation &theta;<sub>u</sub> of the
                steel component.
              </info-tooltip>
            </v-card-title>
            <v-card-text>
              <v-row>
                <v-col v-for="item in memberProperties" :key="item.key" v-bind="variableBind">
                  <unit-slider
                    v-model="variables[item.key]"
                    :label="item.text"
                    :max="item.max"
                    :min="item.min"
                    :unit="item.unit"
                  />
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-col>
    <v-col cols="6">
      <v-img height="200px" :src="publicPath + 'img/connection/component-1.png'" />
      <v-img height="200px" :src="publicPath + 'img/connection/component-2.png'" />
    </v-col>
    <v-col cols="6">
      <v-row>
        <v-col cols="6">
          <v-card>
            <v-card-title>Beams with RBS</v-card-title>
            <v-card-text>
              <unit-chart
                :option="option(backboneWithRbs, envelopeWithRbs)"
                x-unit="rad"
                y-unit="kN⋅mm"
              />
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="6">
          <v-card>
            <v-card-title>Beams without RBS</v-card-title>
            <v-card-text>
              <unit-chart
                :option="option(backboneWithoutRbs, envelopeWithoutRbs)"
                x-unit="rad"
                y-unit="kN⋅mm"
              />
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-col>
    <v-col cols="6">
      <v-card>
        <v-card-title>
          Component Models
          <info-tooltip>Provided that the steel member is in double curvature</info-tooltip>
        </v-card-title>
        <v-card-text>
          <v-table density="compact">
            <thead>
              <tr>
                <th class="text-center" rowspan="2">Parameter</th>
                <th class="text-center" rowspan="2">Unit</th>
                <th class="text-center" colspan="2">Beams with RBS</th>
                <th class="text-center" colspan="2">Beams without RBS</th>
              </tr>
              <tr>
                <th class="text-center">Monotonic Backbone</th>
                <th class="text-center">First Cycle Envelope</th>
                <th class="text-center">Monotonic Backbone</th>
                <th class="text-center">First Cycle Envelope</th>
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
                :columns="[
                  omit(backboneWithRbs, 'points'),
                  omit(envelopeWithRbs, 'points'),
                  omit(backboneWithoutRbs, 'points'),
                  omit(envelopeWithoutRbs, 'points')
                ]"
              />
            </tbody>
          </v-table>
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>
</template>
