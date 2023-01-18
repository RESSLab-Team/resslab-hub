<script setup lang="ts">
import InfoTooltip from "@/components/commons/InfoTooltip.vue";
import SectionSelector from "@/components/commons/SectionSelector.vue";
import UnitSlider, {
  Variable,
} from "@/components/commons/sliders/UnitSlider.vue";
import Toggle, { unitItems } from "@/components/commons/Toggle.vue";
import { publicPath, Section } from "@/utils/common";
import { UnitSystem } from "@/utils/unit";
import { primaryColor, SelectItem } from "@/utils/vuetify";
import { EChartsOption } from "echarts";
import UnitChart from "@/components/commons/charts/UnitChart.vue";

import { computed, reactive, ref, watch } from "vue";

type SteelType = "S235" | "S275" | "S355" | "S420" | "S460";
type Option =
  | "wide-flange"
  | "double-c"
  | "double-l"
  | "round"
  | "square"
  | "l-shape";
interface Result {
  delta_y: number;
  delta_ut: number;
  Nple: number;
  delta_c: number;
  delta_ub: number;
  Nbe: number;
  Nu_c: number;
}

const steelTypes: SteelType[] = ["S235", "S275", "S355", "S420", "S460"];
const options: SelectItem<Option>[] = [
  {
    text: "Wide-Flange",
    value: "wide-flange",
  },
  {
    text: "Double C-shape",
    value: "double-c",
    disabled: true,
  },
  {
    text: "Double L-shape",
    value: "double-l",
    disabled: true,
  },
  {
    text: "Round",
    value: "round",
    disabled: true,
  },
  {
    text: "Square or Rectangular",
    value: "square",
    disabled: true,
  },
  {
    text: "L-shape",
    value: "l-shape",
    disabled: true,
  },
];
const variableBind = {
  cols: "12",
  md: "6",
  xl: "3",
};
const steelShapeDimensions: Variable<keyof Variables>[] = [
  new Variable({
    key: "bf",
    text: "b<sub>f</sub>",
    unit: "mm",
    min: 100,
    max: 500,
  }),
  new Variable({ key: "d", text: "d", unit: "mm", min: 100, max: 2000 }),
  new Variable({
    key: "tf",
    text: "t<sub>f</sub>",
    unit: "mm",
    min: 5,
    max: 100,
  }),
  new Variable({
    key: "tw",
    text: "t<sub>w</sub>",
    unit: "mm",
    min: 5,
    max: 100,
  }),
];
const steelTypeVariables: Variable<keyof Variables>[] = [
  new Variable({
    key: "omega",
    text: "Omega",
    min: 1,
    max: 2,
  }),
  new Variable({
    key: "fy",
    text: "fy",
    unit: "MPa",
    min: 250,
    max: 500,
  }),
];
const additionalParameterVariables: Variable<keyof Variables>[] = [
  new Variable({
    key: "lee",
    text: "Lee",
    min: 1000,
    max: 12000,
  }),
  new Variable({
    key: "lcr",
    text: "Lcr",
    min: 1000,
    max: 12000,
  }),
];

const unitSystem = ref<UnitSystem>("metric");
const section = ref<Section>();
const steelType = ref<SteelType>();
const option = ref<Option>("wide-flange");

interface Variables {
  bf: number;
  d: number;
  tf: number;
  tw: number;
  omega: number;
  fy: number;
  e: number;
  lee: number;
  lcr: number;
  a: number;
  iz: number;
  iy: number;
}
const variables = reactive<Variables>({
  bf: 100,
  d: 100,
  tf: 5,
  tw: 5,
  omega: 1,
  fy: 250,
  e: 210000,
  lee: 8000,
  lcr: 8000,
  a: 10000,
  iz: 10000,
  iy: 1000000,
});

watch(steelType, (value) => {
  switch (value) {
    case "S235":
      variables.omega = 1.45;
      variables.fy = 235;
      return;
    case "S275":
      variables.omega = 1.35;
      variables.fy = 275;
      return;
    case "S355":
      variables.omega = 1.25;
      variables.fy = 255;
      return;
    case "S420":
      variables.omega = 1.25;
      variables.fy = 420;
      return;
    case "S460":
      variables.omega = 1.2;
      variables.fy = 460;
      return;
  }
});

const result = computed<Result>(() => {
  const Imin = Math.min(variables.iz, variables.iy);
  const i = Math.sqrt(Imin / variables.a);

  let lamda_f: number;
  let lamda_CL1: number;
  switch (option.value) {
    case "wide-flange": {
      const c = 10;
      const t = 2;
      lamda_f = c / t;
      lamda_CL1 = 9 * Math.sqrt(235 / variables.fy);
      break;
    }
    default:
      throw new Error(`Unhandled ${option.value}`);
  }
  const NbRd = 1;
  const NplRd = 1;
  const Nple = variables.omega * NplRd;
  const Nbe = variables.omega * NbRd;
  const Nu_c = 0.2 * variables.omega * NbRd;
  const delta_y = 1;
  const delta_c = 1;

  let delta_ub: number;
  let delta_ut: number;
  switch (option.value) {
    case "wide-flange": {
      delta_ub =
        5.6 *
        Math.pow(lamda_f / lamda_CL1, -1.7) *
        Math.pow(
          (variables.lcr / i) *
            Math.sqrt((variables.omega * variables.fy) / variables.e),
          0.4
        ) *
        delta_c;
      delta_ut =
        3.4 *
        Math.pow(lamda_f / lamda_CL1, -1.7) *
        Math.pow(
          (variables.lcr / i) *
            Math.sqrt((variables.omega * variables.fy) / variables.e),
          0.4
        ) *
        delta_y;
      break;
    }
    default:
      throw new Error(`Unhandled ${option.value}`);
  }

  return {
    delta_y: delta_y,
    delta_ut: delta_ut,
    Nple: Nple,
    delta_c: delta_c,
    delta_ub: delta_ub,
    Nbe: Nbe,
    Nu_c: Nu_c,
  };
});

function onSectionChanged(value?: Section): void {
  section.value = value;
  if (value) {
    variables.bf = value.bf;
    variables.d = value.d;
    variables.tf = value.tf;
    variables.tw = value.tw;
  }
}

function getTensionOption(result: Result): EChartsOption {
  return {
    xAxis: {
      name: "Normalized Axial Displacement, δ / δy",
      max: 1.2 * result.delta_ut,
    },
    yAxis: {
      name: "Normalized Axial Resistance, Nt / N",
      max: 1.2 * result.Nple,
    },
    series: [
      {
        type: "line",
        data: [
          [0, 0],
          [result.delta_y, result.Nple],
          [result.delta_ut, result.Nple],
        ],
        color: primaryColor.base,
      },
      {
        type: "line",
        data: [
          [result.delta_ut, result.Nple],
          [result.delta_ut, 0],
        ],
        color: primaryColor.base,
        lineStyle: {
          type: "dashed",
        },
      },
    ],
  };
}

function getCompressionOption(result: Result): EChartsOption {
  return {
    xAxis: {
      name: "Normalized Axial Displacement, δ / δb",
      max: 1.2 * result.delta_ub,
    },
    yAxis: {
      name: "Normalized Axial Resistance, Nc / N",
      max: 1.2 * result.Nbe,
    },
    series: [
      {
        type: "line",
        data: [
          [0, 0],
          [result.delta_c, result.Nbe],
          [result.delta_ub, result.Nu_c],
        ],
        color: primaryColor.base,
      },
      {
        type: "line",
        data: [
          [result.delta_ub, result.Nu_c],
          [result.delta_ub, 0],
        ],
        color: primaryColor.base,
        lineStyle: {
          type: "dashed",
        },
      },
    ],
  };
}
</script>

<template>
  <v-row>
    <v-col cols="12">
      <v-row align="center">
        <v-col>
          <h1>Component Model for Steel Bracings</h1>
          <p>
            This web-based interactive interface computes the basic parameters
            for predictive modeling of steel bracings based on their basic
            material and geometric properties. For further information refer to
            Eurocode 8 Part 3.
          </p>
        </v-col>
        <v-col cols="auto">
          <toggle v-model="unitSystem" :items="unitItems"></toggle>
        </v-col>
      </v-row>
    </v-col>
    <v-col cols="6">
      <v-row>
        <v-col>
          <v-card>
            <v-card-title>
              Select cross section type
              <info-tooltip>
                Select the cross-sectional shape of the bracing member
              </info-tooltip>
            </v-card-title>
            <v-card-text>
              <v-col v-bind="variableBind">
                <v-select
                  v-model="option"
                  clearable
                  hide-details
                  :items="options"
                  label="Select Option"
                  single-line
                ></v-select> </v-col
            ></v-card-text>
          </v-card>
        </v-col>
      </v-row>
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
              <section-selector
                @update:section="onSectionChanged($event)"
              ></section-selector>
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
                    :unit-system="unitSystem"
                  ></unit-slider>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <v-card>
            <v-card-title
              >Steel Type
              <info-tooltip
                >Select a standard steel grade or specify manually the material
                overstrength (Omega) and the nominal yield strength,
                fy)</info-tooltip
              ></v-card-title
            >
            <v-card-text>
              <v-row>
                <v-col v-bind="variableBind">
                  <v-select
                    v-model="steelType"
                    clearable
                    hide-details
                    :items="steelTypes"
                    label="Select Steel Type"
                    single-line
                  ></v-select>
                </v-col>
              </v-row>
              <v-row>
                <v-col
                  v-for="item in steelTypeVariables"
                  :key="item.key"
                  v-bind="variableBind"
                >
                  <unit-slider
                    v-model="variables[item.key]"
                    :disabled="!!steelType"
                    :label="item.text"
                    :max="item.max"
                    :min="item.min"
                    :unit="item.unit"
                    :unit-system="unitSystem"
                  ></unit-slider>
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
        :src="publicPath + 'img/brace/I_shaped_Bracing.png'"
      ></v-img>
    </v-col>
    <v-col cols="6">
      <v-card>
        <v-card-title
          >Associated Member Lengths
          <info-tooltip
            >Specify the associated member lengths as defined in the definition
            in the upper left corner</info-tooltip
          ></v-card-title
        >
        <v-card-text>
          <v-row>
            <v-col
              v-for="item in additionalParameterVariables"
              :key="item.key"
              v-bind="variableBind"
            >
              <unit-slider
                v-model="variables[item.key]"
                :label="item.text"
                :max="item.max"
                :min="item.min"
                :unit="item.unit"
                :unit-system="unitSystem"
              ></unit-slider>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>
    </v-col>
    <v-col cols="3">
      <v-card>
        <v-card-title>Tension</v-card-title>
        <v-card-text>
          <unit-chart
            :option="getTensionOption(result)"
            :unit-system="unitSystem"
          ></unit-chart>
        </v-card-text>
      </v-card>
    </v-col>
    <v-col cols="3">
      <v-card>
        <v-card-title>Compression</v-card-title>
        <v-card-text>
          <unit-chart
            :option="getCompressionOption(result)"
            :unit-system="unitSystem"
          ></unit-chart>
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>
</template>
