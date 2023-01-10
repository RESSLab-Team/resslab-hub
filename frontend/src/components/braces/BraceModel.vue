<script setup lang="ts">
import InfoTooltip from "@/components/commons/InfoTooltip.vue";
import SectionSelector from "@/components/commons/SectionSelector.vue";
import UnitSlider, {
  Variable,
} from "@/components/commons/sliders/UnitSlider.vue";
import Toggle, { unitItems } from "@/components/commons/Toggle.vue";
import { publicPath, Section } from "@/utils/common";
import { UnitSystem } from "@/utils/unit";
import { SelectItemObject } from "@/utils/vuetify";

import { reactive, ref, Ref, watch } from "vue";

type SteelType = "S235" | "S275" | "S355" | "S420" | "S460";
type Option =
  | "wide-flange"
  | "double-c"
  | "double-l"
  | "round"
  | "square"
  | "l-shape";

const steelTypes: SteelType[] = ["S235", "S275", "S355", "S420", "S460"];
const options: SelectItemObject<Option>[] = [
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
const steelShapeDimensions: Variable[] = [
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
const steelTypeVariables: Variable[] = [
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
const additionalParameterVariables: Variable[] = [
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

const unitSystem: Ref<UnitSystem> = ref("metric");
const section: Ref<Section | undefined> = ref();
const steelType: Ref<SteelType | undefined> = ref();
const option: Ref<Option> = ref("wide-flange");

const variables = reactive({
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

function onSectionChanged(value: Section): void {
  section.value = value ?? null;
  if (value) {
    variables.bf = value.bf;
    variables.d = value.d;
    variables.tf = value.tf;
    variables.tw = value.tw;
  }
}
</script>

<template>
  <v-row>
    <v-col cols="12">
      <v-row align="center">
        <v-col>
          <h1>Backbone Curve Plotter for Steel Components</h1>
          <p>
            Construct the backbone curve of beams with RBS and beams
            other-than-RBS. For further information refer to
            <a
              href="http://ascelibrary.org/doi/abs/10.1061/(ASCE)ST.1943-541X.0000376"
              target="_blank"
            >
              Lignos and Krawinkler (2011)
            </a>
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
            <v-card-title>Steel Type</v-card-title>
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
        <v-card-title>Additional Parameters</v-card-title>
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
            <v-col v-bind="variableBind">
              <v-select
                v-model="option"
                clearable
                hide-details
                :items="options"
                label="Select Option"
                single-line
              ></v-select>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>
</template>
