<script setup lang="ts">
// Computations from https://github.com/RESSLab-Team/resslab-hub-scripts/tree/main/steel_beams
import UnitChart from '@/components/commons/charts/UnitChart.vue'
import InfoTooltip from '@/components/commons/InfoTooltip.vue'
import SectionSelector from '@/components/commons/SectionSelector.vue'
import ToolSlider from '@/components/commons/tools/ToolSlider.vue'
import type { Variable } from '@/utils/model'
import PageHeader from '@/components/commons/PageHeader.vue'
import UnitTableRow, { type UnitTableRowData } from '@/components/commons/UnitTableRow.vue'
import UnitToggle from '@/components/commons/UnitToggle.vue'
import { publicPath, type Section } from '@/utils/common'
import type { Point } from '@/utils/model'
import { primaryColor, secondaryColor } from '@/utils/vuetify'
import type { EChartsOption } from 'echarts'
import { clamp, omit } from 'lodash'
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })

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
      ((2 * tf * Math.pow(bf, 3)) / 12 + ((d - 2 * tf) * Math.pow(tw, 3)) / 12) /
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
  const zx = getZx(false)
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
    Math.pow(e / (fy / 1000), 0.23)
  const thetaPc = clamp(
    2.5 *
      Math.pow(h / tw, -1.1) *
      Math.pow(bf / 2 / tf, -0.1) *
      Math.pow(lb / ry, -0.1) *
      Math.pow(e / (fy / 1000), 0.09),
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
      495 * Math.pow(h / tw, -1.34) * Math.pow(bf / 2 / tf, -0.595) * Math.pow(fy / 355, -0.36),
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
      536 *
        Math.pow(h / tw, -1.26) *
        Math.pow(bf / 2 / tf, -0.525) *
        Math.pow(lb / ry, -0.13) *
        Math.pow(fy / 355, -0.291),
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
    Math.pow(e / (fy / 1000), 0.2)
  const thetaPc = clamp(
    6.4 *
      Math.pow(h / tw, -0.9) *
      Math.pow(bf / 2 / tf, -0.2) *
      Math.pow(lb / ry, -0.5) *
      Math.pow(e / (fy / 1000), 0.1),
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
  return 2 * (n * bf * tf * ((d - tf) / 2) + (Math.pow(d - 2 * tf, 2) * tw) / 8)
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
      name: t('tools.connection_model.chart_x_axis')
    },
    yAxis: {
      name: t('tools.connection_model.chart_y_axis')
    },
    series: [
      {
        type: 'line',
        name: t('tools.connection_model.series_monotonic_backbone'),
        data: backbone.points,
        color: primaryColor.base
      },
      {
        type: 'line',
        name: t('tools.connection_model.series_first_cycle_envelope'),
        data: envelope.points,
        color: secondaryColor.base
      }
    ]
  }
}

defineExpose({
  vars,
  backboneRbs,
  backboneNonRbs,
  envelopeRbs,
  envelopeNonRbs,
  variables,
  onSectionChanged
})
</script>

<template>
  <div class="tool-page">
    <page-header
      :eyebrow="$t('tools.common.model_eyebrow')"
      :title="$t('tools.connection_model.title')"
    >
      <template #actions><unit-toggle /></template>
      <i18n-t keypath="tools.connection_model.intro" tag="span" scope="global">
        <template #reference>
          <a
            href="http://ascelibrary.org/doi/abs/10.1061/(ASCE)ST.1943-541X.0000376"
            target="_blank"
          >
            {{ $t('tools.connection_model.intro_reference') }}
          </a>
        </template>
      </i18n-t>
    </page-header>
    <div class="tool-shell">
      <div class="frag-a">
        <aside class="tool-panel">
          <div class="tool-card">
            <div class="tool-card-h with-info">
              {{ $t('tools.connection_model.select_steel_profile') }}
              <info-tooltip>{{
                $t('tools.connection_model.select_steel_profile_help')
              }}</info-tooltip>
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
              {{ $t('tools.connection_model.specify_member_properties') }}
              <info-tooltip>{{
                $t('tools.connection_model.specify_member_properties_help')
              }}</info-tooltip>
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

          <figure class="tool-schematic is-small">
            <img
              :alt="$t('tools.connection_model.schematic_alt')"
              :src="publicPath + 'img/connection/component-1.png'"
            />
            <img
              :alt="$t('tools.connection_model.schematic_alt')"
              :src="publicPath + 'img/connection/component-2.png'"
            />
          </figure>
        </aside>

        <section class="tool-chart-col">
          <div class="tool-chart-grid tool-fit-primary">
            <div class="mat-focus">
              <h2 class="tool-chart-h">{{ $t('tools.connection_model.chart_beams_with_rbs') }}</h2>
              <unit-chart
                fit
                :option="option(backboneWithRbs, envelopeWithRbs)"
                x-unit="rad"
                y-unit="kN⋅mm"
              />
            </div>
            <div class="mat-focus">
              <h2 class="tool-chart-h">
                {{ $t('tools.connection_model.chart_beams_without_rbs') }}
              </h2>
              <unit-chart
                fit
                :option="option(backboneWithoutRbs, envelopeWithoutRbs)"
                x-unit="rad"
                y-unit="kN⋅mm"
              />
            </div>
          </div>

          <div class="tool-card tool-fit-scroll">
            <div class="tool-card-h with-info">
              {{ $t('tools.connection_model.component_models') }}
              <info-tooltip>{{ $t('tools.connection_model.component_models_help') }}</info-tooltip>
            </div>
            <v-table density="compact">
              <thead>
                <tr>
                  <th class="text-center" rowspan="2">
                    {{ $t('tools.connection_model.table_parameter') }}
                  </th>
                  <th class="text-center" rowspan="2">
                    {{ $t('tools.connection_model.table_unit') }}
                  </th>
                  <th class="text-center" colspan="2">
                    {{ $t('tools.connection_model.table_beams_with_rbs') }}
                  </th>
                  <th class="text-center" colspan="2">
                    {{ $t('tools.connection_model.table_beams_without_rbs') }}
                  </th>
                </tr>
                <tr>
                  <th class="text-center">
                    {{ $t('tools.connection_model.table_monotonic_backbone') }}
                  </th>
                  <th class="text-center">
                    {{ $t('tools.connection_model.table_first_cycle_envelope') }}
                  </th>
                  <th class="text-center">
                    {{ $t('tools.connection_model.table_monotonic_backbone') }}
                  </th>
                  <th class="text-center">
                    {{ $t('tools.connection_model.table_first_cycle_envelope') }}
                  </th>
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
          </div>
        </section>
      </div>
    </div>
  </div>
</template>
