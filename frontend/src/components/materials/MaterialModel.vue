<script setup lang="ts">
import InfoTooltip from "@/components/commons/InfoTooltip.vue";
import Toggle, { unitItems } from "@/components/commons/Toggle.vue";
import { variableBind } from "@/utils/model";
import { UnitSystem } from "@/utils/unit";
import { SelectItemObject } from "@/utils/vuetify";
import { computed, onMounted, reactive, ref, watch } from "vue";
import UnitSlider, {
  Variable,
} from "@/components/commons/sliders/UnitSlider.vue";
import UnitLineChart from "@/components/commons/charts/UnitLineChart.vue";
import { materialsApi } from "@/plugins/axios";
import { LineSeriesOption } from "echarts";
import { computeUvcStress } from "@/utils/material";
import { zip } from "lodash";
import Snackbar from "@/components/commons/Snackbar.vue";
import materialParameters from "@/assets/material/parameter-material-list.csv";

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

const materialSelectItems: SelectItemObject<Material>[] =
  materialParameters.map((item) => ({
    text: item.steel,
    value: {
      e: item.E,
      sigma: item.syo,
      q: item.Q_inf,
      b: item.b,
      d: item.D_inf,
      a: item.a,
      c1: item.c1,
      gamma1: item.gamma1,
      c2: item.c2,
      gamma2: item.gamma2,
    },
  }));

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
        return [
          id,
          {
            data: zip(strain, stress),
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
          <toggle v-model="unitSystem" :items="unitItems" />
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
          <unit-line-chart
            :series="[chartSeries[item.id]]"
            :title="item.title"
            :unit-system="unitSystem"
            x-axis-name="ε"
            y-axis-name="σ"
            y-unit="MPa"
          />
        </v-col>
      </v-row>
    </v-col>
    <snackbar ref="snackbar" />
  </v-row>
</template>
