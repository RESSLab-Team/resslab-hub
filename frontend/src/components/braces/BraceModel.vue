<script setup lang="ts">
import InfoTooltip from "@/components/commons/InfoTooltip.vue";
import SectionSelector from "@/components/commons/SectionSelector.vue";
import UnitSlider, {
  Variable,
} from "@/components/commons/sliders/UnitSlider.vue";
import Toggle, { unitItems } from "@/components/commons/Toggle.vue";
import { publicPath, Section } from "@/utils/common";
import { UnitSystem } from "@/utils/unit";
import { reactive, ref, Ref } from "vue";

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

const unitSystem: Ref<UnitSystem> = ref("metric");
const section: Ref<Section> = ref();
const variables = reactive({
  bf: 100,
  d: 100,
  tf: 5,
  tw: 5,
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
    </v-col>
    <v-col cols="6">
      <v-img
        contain
        :src="publicPath + 'img/brace/I_shaped_Bracing.png'"
      ></v-img>
    </v-col>
  </v-row>
</template>
