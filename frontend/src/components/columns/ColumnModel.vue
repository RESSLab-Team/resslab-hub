<script setup lang="ts">
// Computations from https://github.com/RESSLab-Team/resslab-hub-scripts/tree/main/steel_columns
import UnitChart from "@/components/commons/charts/UnitChart.vue";
import InfoTooltip from "@/components/commons/InfoTooltip.vue";
import UnitSlider, {
  Variable,
} from "@/components/commons/sliders/UnitSlider.vue";
import UnitTableRow, {
  UnitTableRowData,
} from "@/components/commons/UnitTableRow.vue";
import { publicPath, Section } from "@/utils/common";
import { variableBind } from "@/utils/model";
import { primaryColor, secondaryColor } from "@/utils/vuetify";
import { EChartsOption } from "echarts";
import { clamp } from "lodash";
import { computed, reactive, ref } from "vue";
import { Point } from "@/utils/model";
import SectionSelector from "@/components/commons/SectionSelector.vue";

interface Result {
  ke: number;
  my: number;
  mc: number;
  mRes: number;
  thetaP: number;
  thetaPc: number;
  thetaUlt: number;
  lamdba?: number;
  points: Point[];
}

interface Envelope {
  thetaY: number;
  mc: number;
  thetaP: number;
  thetaPc: number;
  res: number;
  mRes: number;
  thetaUlt: number;
  alpha: number;
  alphaPc: number;
}

interface Backbone extends Envelope {
  a: number;
  lambda: number;
}

const steelShapeDimensions: Variable<keyof Variables>[] = [
  {
    key: "bf",
    text: "b<sub>f</sub>",
    unit: "mm",
    min: 100,
    max: 500,
  },
  { key: "d", text: "d", unit: "mm", min: 100, max: 2000 },
  {
    key: "tf",
    text: "t<sub>f</sub>",
    unit: "mm",
    min: 5,
    max: 100,
  },
  {
    key: "tw",
    text: "t<sub>w</sub>",
    unit: "mm",
    min: 5,
    max: 100,
  },
];
const memberProperties: Variable<keyof Variables>[] = [
  {
    key: "pgPye",
    text: "P<sub>g</sub>/P<sub>ye</sub>",
    min: 0,
    max: 1,
  },
  {
    key: "l",
    text: "L",
    unit: "mm",
    min: 1000,
    max: 12000,
  },
  {
    key: "lb",
    text: "L<sub>b</sub>",
    unit: "mm",
    min: 1000,
    max: 12000,
  },
  {
    key: "fy",
    text: "F<sub>y</sub>",
    unit: "MPa",
    min: 250,
    max: 500,
  },
];
const rows: UnitTableRowData[] = [
  {
    key: "ke",
    text: "K<sub>e</sub>",
    unit: "<sup>kN⋅mm</sup>/<sub>rad</sub>",
    fractionDigit: 0,
  },
  {
    key: "my",
    text: "M<sub>y</sub>",
    unit: "kN⋅mm",
    fractionDigit: 0,
  },
  {
    key: "mc",
    text: "M<sub>c</sub>",
    unit: "kN⋅mm",
    fractionDigit: 0,
  },
  {
    key: "mRes",
    text: "M<sub>r</sub>",
    unit: "kN⋅mm",
    fractionDigit: 0,
  },
  {
    key: "thetaP",
    text: "&theta;<sub>p</sub>",
    unit: "rad",
    fractionDigit: 3,
  },
  {
    key: "thetaPc",
    text: "&theta;<sub>pc</sub>",
    unit: "rad",
    fractionDigit: 3,
  },
  {
    key: "thetaUlt",
    text: "&theta;<sub>u</sub>",
    unit: "rad",
    fractionDigit: 3,
  },
  {
    key: "lamdba",
    text: "&Lambda;",
    unit: "rad",
    fractionDigit: 3,
  },
];

const section = ref<Section>();

interface Variables {
  e: number;
  bf: number;
  d: number;
  tf: number;
  tw: number;
  pgPye: number;
  l: number;
  lb: number;
  fy: number;
}
const variables = reactive<Variables>({
  e: 205,
  bf: 100,
  d: 100,
  tf: 5,
  tw: 5,
  pgPye: 0.2,
  l: 5000,
  lb: 5000,
  fy: 380,
});

const vars = computed(() => {
  const h = section.value ? section.value.h : variables.d - 2 * variables.tf;
  const ix = section.value
    ? section.value.ix
    : (Math.pow(variables.d - 2 * variables.tf, 3) * variables.tw) / 12 +
      2 *
        variables.bf *
        variables.tf *
        (Math.pow(variables.tf, 2) / 12 +
          Math.pow((variables.d - variables.tf) / 2, 2));
  const ry = section.value
    ? section.value.ry
    : Math.sqrt(
        ((variables.tf * Math.pow(variables.bf, 3)) / 12 +
          ((variables.d - 2 * variables.tf) * Math.pow(variables.tw, 3)) / 12) /
          (2 * variables.tf * variables.bf +
            (variables.d - 2 * variables.tf) * variables.tw)
      );
  const ke = (6 * variables.e * ix) / variables.l;
  const zx = section.value
    ? section.value.zx
    : 2 *
      (variables.bf * variables.tf * ((variables.d - variables.tf) / 2) +
        (Math.pow(variables.d - 2 * variables.tf, 2) * variables.tw) / 4);
  const my =
    variables.pgPye < 0.2
      ? 1.15 * zx * (variables.fy / 1000) * (1 - variables.pgPye / 2)
      : 1.15 * zx * (variables.fy / 1000) * (9 / 8) * (1 - variables.pgPye);
  return {
    h,
    ix,
    ry,
    ke,
    zx,
    my,
  };
});

const backbone = computed<Backbone>(() => {
  const a = clamp(
    12.5 *
      Math.pow(vars.value.h / variables.tw, -0.2) *
      Math.pow(variables.lb / vars.value.ry, -0.4) *
      Math.pow(1 - variables.pgPye, 0.4),
    1,
    1.3
  );
  const mc = a * vars.value.my;
  const res = 0.5 - 0.4 * variables.pgPye;
  const mRes = res * vars.value.my;
  const thetaY = vars.value.my / vars.value.ke;
  const thetaP = Math.min(
    0.2,
    294 *
      Math.pow(vars.value.h / variables.tw, -1.7) *
      Math.pow(variables.lb / vars.value.ry, -0.7) *
      Math.pow(1 - variables.pgPye, 1.6)
  );
  const thetaPc = Math.min(
    0.3,
    90 *
      Math.pow(vars.value.h / variables.tw, -0.8) *
      Math.pow(variables.lb / vars.value.ry, -0.8) *
      Math.pow(1 - variables.pgPye, 2.5)
  );
  const thetaUlt = 0.15;
  const alpha = (mc - vars.value.my) / thetaP / vars.value.ke;
  const alphaPc = -mc / (vars.value.ke * thetaPc);
  const lambda =
    variables.pgPye <= 0.35
      ? Math.min(
          3.0,
          25000 *
            Math.pow(vars.value.h / variables.tw, -2.14) *
            Math.pow(variables.lb / vars.value.ry, -0.53) *
            Math.pow(1 - variables.pgPye, 4.92)
        )
      : Math.min(
          3.0,
          268000 *
            Math.pow(vars.value.h / variables.tw, -2.3) *
            Math.pow(variables.lb / vars.value.ry, -1.3) *
            Math.pow(1 - variables.pgPye, 1.19)
        );
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
    lambda,
  };
});
const envelope = computed<Envelope>(() => {
  const a = clamp(
    9.5 *
      Math.pow(vars.value.h / variables.tw, -0.4) *
      Math.pow(variables.lb / vars.value.ry, -0.16) *
      Math.pow(1 - variables.pgPye, 0.2),
    1,
    1.3
  );
  const mc = a * vars.value.my;
  const res = 0.4 - 0.4 * variables.pgPye;
  const mRes = res * vars.value.my;
  const thetaY = vars.value.my / vars.value.ke;
  const thetaP = Math.min(
    0.1,
    15 *
      Math.pow(vars.value.h / variables.tw, -1.6) *
      Math.pow(variables.lb / vars.value.ry, -0.3) *
      Math.pow(1 - variables.pgPye, 2.3)
  );
  const thetaPc = Math.min(
    0.1,
    14 *
      Math.pow(vars.value.h / variables.tw, -0.8) *
      Math.pow(variables.lb / vars.value.ry, -0.5) *
      Math.pow(1 - variables.pgPye, 3.2)
  );
  const thetaUlt = 0.08 * (1 - 0.6 * variables.pgPye);
  const alpha = (mc - vars.value.my) / thetaP / vars.value.ke;
  const alphaPc = -mc / (vars.value.ke * thetaPc);
  return {
    thetaY,
    mc,
    thetaP,
    thetaPc,
    res,
    mRes,
    thetaUlt,
    alpha,
    alphaPc,
  };
});
const backboneResult = computed<Result>(() => getResult(backbone.value));
const envelopeResult = computed<Result>(() => getResult(envelope.value));

function onSectionChanged(value?: Section): void {
  section.value = value;
  if (value) {
    variables.bf = value.bf;
    variables.d = value.d;
    variables.tf = value.tf;
    variables.tw = value.tw;
  }
}

function getPoints(output: Envelope | Backbone): Point[] {
  const p1: Point = [0, 0];
  const p2: Point = [output.thetaY, vars.value.my];
  const p3: Point = [p2[0] + output.thetaP, output.mc];
  const p4: Point = [
    p3[0] + (output.mc - output.mRes) / (-output.alphaPc * vars.value.ke),
    output.mRes,
  ];
  if (p4[0] < output.thetaUlt) {
    const p5: Point = [output.thetaUlt, output.mRes];
    const p6: Point = [p5[0], 0];
    return [p1, p2, p3, p4, p5, p6];
  } else if (p3[0] < output.thetaUlt) {
    // && output.thetaUlt <= p4[0]
    const p5: Point = [
      output.thetaUlt,
      output.mc +
        output.alphaPc *
          vars.value.ke *
          Math.abs(output.thetaPc - output.thetaUlt),
    ];
    const p6: Point = [p5[0], 0];
    return [p1, p2, p3, p5, p6];
  } else if (p2[0] < output.thetaUlt) {
    // && output.thetaUlt <= p3[0]
    const p5: Point = [
      output.thetaUlt,
      vars.value.my +
        output.alpha * vars.value.ke * (output.thetaUlt - output.thetaY),
    ];
    const p6: Point = [p5[0], 0];
    return [p1, p2, p5, p6];
  } else {
    const p5: Point = [output.thetaUlt, vars.value.ke * output.thetaUlt];
    const p6: Point = [p5[0], 0];
    return [p1, p5, p6];
  }
}

function getResult(output: Envelope | Backbone): Result {
  return {
    ke: vars.value.ke,
    my: vars.value.my,
    lamdba: (output as Backbone).lambda,
    ...output,
    points: getPoints(output),
  };
}

function option(backbone: Result, envelope: Result): EChartsOption {
  return {
    xAxis: {
      name: "Chord Rotation, θ",
    },
    yAxis: {
      name: "Moment, M",
    },
    series: [
      {
        type: "line",
        name: "Monotonic Backbone",
        data: backbone.points,
        color: primaryColor.base,
      },
      {
        type: "line",
        name: "First-Cycle Envelope",
        data: envelope.points,
        color: secondaryColor.base,
      },
    ],
  };
}
</script>

<template>
  <v-row>
    <v-col cols="12">
      <h1>Predictive Model for Steel wide Flange Columns</h1>
      <p>
        For further information refer to
        <a href="" target="_blank"> Lignos et al. (2019) </a>
      </p>
    </v-col>
    <v-col cols="6">
      <v-row>
        <v-col>
          <v-card>
            <v-card-title>
              Select Steel Profile
              <info-tooltip>
                Here, you may choose to either select a W-Shape from the AISC
                database or input your own dimensions using the sliders below
              </info-tooltip>
            </v-card-title>
            <v-card-text>
              <section-selector @update:section="onSectionChanged($event)" />
              <v-row>
                <v-col
                  v-for="item in steelShapeDimensions"
                  :key="item.key"
                  v-bind="variableBind"
                >
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
              Specify Member and Loading Properties
              <info-tooltip>
                Here you need to specify the beam full length (L), the beam
                unbraced length (L<sub>b</sub>), which is defined as the
                distance from the column face to the nearest lateral brace, the
                expected yield stress, F<sub>y</sub> of the steel material, the
                capping-to-yield ratio <sup>Mc</sup>/<sub>My</sub>, the expected
                residual strength ratio, K, and the ultimate rotation
                &theta;<sub>u</sub> of the steel component.
              </info-tooltip>
            </v-card-title>
            <v-card-text>
              <v-row>
                <v-col
                  v-for="item in memberProperties"
                  :key="item.key"
                  v-bind="variableBind"
                >
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
      <v-img
        contain
        height="400px"
        :src="publicPath + 'img/column/component.png'"
      />
    </v-col>
    <v-col cols="6">
      <v-row justify="center">
        <v-col cols="6">
          <v-card>
            <v-card-text>
              <unit-chart
                :option="option(backboneResult, envelopeResult)"
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
          Predictive Model for Columns
          <info-tooltip>
            Provided that the steel member is in double curvature
          </info-tooltip>
        </v-card-title>
        <v-card-text>
          <v-simple-table dense>
            <template #default>
              <thead>
                <tr>
                  <th class="text-center">Parameter</th>
                  <th class="text-center">Unit</th>
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
                  :columns="[backboneResult, envelopeResult]"
                />
              </tbody>
            </template>
          </v-simple-table>
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>
</template>
