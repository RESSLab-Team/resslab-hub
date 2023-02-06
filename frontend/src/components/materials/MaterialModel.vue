<script setup lang="ts">
import InfoTooltip from "@/components/commons/InfoTooltip.vue";
import Toggle, { unitItems } from "@/components/commons/Toggle.vue";
import { variableBind } from "@/utils/model";
import { Unit, units, UnitSystem } from "@/utils/unit";
import { SelectItemObject } from "@/utils/vuetify";
import { computed, onMounted, reactive, ref, watch } from "vue";
import UnitSlider, {
  Variable,
} from "@/components/commons/sliders/UnitSlider.vue";
import MultipleLineChart from "@/components/commons/charts/MultipleLineChart.vue";
import { materialsApi } from "@/plugins/axios";
import { LineSeriesOption } from "echarts";
import { computeUvcStress } from "@/utils/material";
import { zip } from "lodash";
import Snackbar from "@/components/commons/Snackbar.vue";

interface Material {
  e: number;
  sigma: number;
  q: number;
  b: number;
  d: number;
  a: number;
  c1: number;
  gamma1: number;
  c2: number;
  gamma2: number;
}

const materialSelectItems: SelectItemObject<Material>[] = [
  {
    text: "S355 J2+N (plate)",
    value: {
      e: 200000,
      sigma: 355,
      q: 120.5,
      b: 8.14,
      d: 93.15,
      a: 261.75,
      c1: 21102,
      gamma1: 173.6,
      c2: 2300.6,
      gamma2: 10.42,
    },
  },
  {
    text: "S355 J2 (H-shape)",
    value: {
      e: 200000,
      sigma: 355,
      q: 138.01,
      b: 11.36,
      d: 96.16,
      a: 223.66,
      c1: 18574.8,
      gamma1: 257.75,
      c2: 1351.98,
      gamma2: 6.52,
    },
  },
  {
    text: "S460 NL (plate)",
    value: {
      e: 200000,
      sigma: 460,
      q: 97.35,
      b: 14.02,
      d: 136.64,
      a: 226.4,
      c1: 26691,
      gamma1: 185.75,
      c2: 2892.4,
      gamma2: 10.44,
    },
  },
  {
    text: "S690 QL (plate)",
    value: {
      e: 200000,
      sigma: 690,
      q: 0.11,
      b: 0.11,
      d: 132.3,
      a: 285.15,
      c1: 34575,
      gamma1: 185.16,
      c2: 3154.2,
      gamma2: 20.14,
    },
  },
  {
    text: "A992 Gr. 50 (wide-flange)",
    value: {
      e: 200000,
      sigma: 345,
      q: 141.45,
      b: 15.2,
      d: 135.95,
      a: 211.16,
      c1: 25621,
      gamma1: 235.12,
      c2: 942.18,
      gamma2: 3.16,
    },
  },
  {
    text: "A500 Gr. B (tube)",
    value: {
      e: 200000,
      sigma: 315,
      q: 228.02,
      b: 0.11,
      d: 50.41,
      a: 270.4,
      c1: 17707,
      gamma1: 207.18,
      c2: 1526.2,
      gamma2: 6.22,
    },
  },
  {
    text: "BCP 325 (tube)",
    value: {
      e: 200000,
      sigma: 325,
      q: 112.25,
      b: 10.78,
      d: 105.95,
      a: 221.92,
      c1: 20104,
      gamma1: 200.43,
      c2: 2203,
      gamma2: 11.76,
    },
  },
  {
    text: "BCR 295 (tube)",
    value: {
      e: 200000,
      sigma: 295,
      q: 0.09,
      b: 0.09,
      d: 103.3,
      a: 212.83,
      c1: 20750.59,
      gamma1: 225.26,
      c2: 1245.04,
      gamma2: 2.09,
    },
  },
  {
    text: "HYP 400 (plate)",
    value: {
      e: 200000,
      sigma: 400,
      q: 62.63,
      b: 16.57,
      d: 109.28,
      a: 145.74,
      c1: 13860,
      gamma1: 141.61,
      c2: 1031.18,
      gamma2: 3.53,
    },
  },
];

const materialVariables: Variable<keyof Material>[] = [
  {
    key: "e",
    text: "E",
    unit: "MPa",
    min: 190000,
    max: 210000,
  },
  {
    key: "sigma",
    text: "σ<sub>y0</sub>",
    min: 200,
    max: 700,
    unit: "MPa",
  },
  {
    key: "q",
    text: "Q<sub>00</sub>",
    min: 0,
    max: 300,
    unit: "MPa",
  },
  {
    key: "b",
    text: "b",
    min: 0,
    max: 30,
  },
  {
    key: "d",
    text: "D<sub>00</sub>",
    min: 0,
    max: 200,
    unit: "MPa",
  },
  {
    key: "a",
    text: "a",
    min: 100,
    max: 400,
  },
  {
    key: "c1",
    text: "c<sub>1</sub>",
    min: 5000,
    max: 40000,
    unit: "MPa",
  },
  {
    key: "gamma1",
    text: "γ<sub>1</sub>",
    min: 100,
    max: 400,
  },
  {
    key: "c2",
    text: "c<sub>2</sub>",
    min: 0,
    max: 5000,
    unit: "MPa",
  },
  {
    key: "gamma2",
    text: "γ<sub>2</sub>",
    min: 0,
    max: 50,
  },
];
type testId = "LP1_S1_C" | "LP6_S1_C" | "LP9_S1_D" | "LP5_S1_D";
const charts: { title: string; id: testId }[] = [
  { title: "Monotonic tensile", id: "LP1_S1_C" },
  { title: "Symmetric cyclic", id: "LP6_S1_C" },
  { title: "Random", id: "LP9_S1_D" },
  { title: "Constant amplitude", id: "LP5_S1_D" },
];

const snackbar = ref<Snackbar>();
const unitSystem = ref<UnitSystem>("metric");
const selectedMaterial = ref<Material>(materialSelectItems[0].value);
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
  gamma2: 0,
});
const strains = ref<Record<testId, number[]>>({
  LP1_S1_C: [],
  LP6_S1_C: [],
  LP9_S1_D: [],
  LP5_S1_D: [],
});
const chartSeries = computed<Record<testId, LineSeriesOption>>(() => {
  return Object.fromEntries(
    Object.entries(strains.value).map(([id, strain]) => {
      try {
        const stress = computeUvcStress(
          strain,
          variables.e,
          variables.sigma,
          variables.q,
          variables.b,
          variables.d,
          variables.a,
          [
            {
              c: variables.c1,
              gamma: variables.gamma1,
            },
            {
              c: variables.c2,
              gamma: variables.gamma2,
            },
          ]
        );

        const imperialUnit = units.find(
            (d) => d.referenceUnit === "MPa" && d.unit === "ksi"
          ) as Unit,
          mapToImperial = (stress: number) =>
            unitSystem.value === "metric"
              ? stress
              : stress / imperialUnit.ratio;

        return [
          id,
          {
            data: zip(strain, stress.map(mapToImperial)),
          } as LineSeriesOption,
        ];
      } catch (error) {
        snackbar.value?.open(error as string);
        return [
          id,
          {
            data: [[]],
          } as LineSeriesOption,
        ];
      }
    })
  ) as Record<testId, LineSeriesOption>;
});

onMounted(() => {
  Promise.all(
    Object.keys(strains.value).map((id) =>
      materialsApi
        .getMaterialsStressStrain(id)
        .then(
          (response) =>
            [id, response.data.map((serie) => serie[1])] as [testId, number[]]
        )
    )
  ).then(
    (entries) =>
      (strains.value = Object.fromEntries(entries) as Record<testId, number[]>)
  );
});

watch(
  selectedMaterial,
  (material) => {
    Object.assign(variables, material);
  },
  { immediate: true }
);
</script>

<template>
  <v-row>
    <v-col cols="12">
      <v-row align="center">
        <v-col>
          <h1>Material Model</h1>
          <p>
            This web based interactive interface computes the hysteretic
            behavior of typical steels under inelastic cyclic straining. For
            further information refer to
            <a
              href="https://ascelibrary.org/doi/abs/10.1061/%28ASCE%29ST.1943-541X.0002964"
              target="_blank"
              >Hartloper et al. (2021)</a
            >
            The uniaxial loading protocols are based on work by
            <a
              href="https://ascelibrary.org/doi/full/10.1061/%28ASCE%29EM.1943-7889.0001922"
              target="_blank"
              >de Castro e Sousa et al. (2020)</a
            >
          </p>
        </v-col>
        <v-col cols="auto">
          <toggle v-model="unitSystem" :items="unitItems"></toggle>
        </v-col>
      </v-row>
    </v-col>
    <v-col cols="6">
      <v-card>
        <v-card-title>
          Select Steel Material
          <info-tooltip>TODO</info-tooltip>
        </v-card-title>
        <v-card-text>
          <v-row>
            <v-col v-bind="variableBind">
              <v-select
                v-model="selectedMaterial"
                :items="materialSelectItems"
              />
            </v-col>
          </v-row>
          <v-row>
            <v-col
              v-for="item in materialVariables"
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
              />
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>
    </v-col>
    <v-col cols="6">
      <v-row>
        <v-col v-for="item in charts" :key="item.title" cols="6">
          <multiple-line-chart
            :title="item.title"
            x-axis-name="ε"
            :y-axis-name="`σ [${unitSystem === 'metric' ? 'MPa' : 'ksi'}]`"
            :series="[chartSeries[item.id]]"
          />
        </v-col>
      </v-row>
    </v-col>
    <snackbar ref="snackbar" />
  </v-row>
</template>
