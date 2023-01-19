<script setup lang="ts">
// Computations from https://github.com/RESSLab-Team/resslab-hub-scripts/tree/main/fragility_curves_steel_connections
import UnitChart from "@/components/commons/charts/UnitChart.vue";
import UnitSlider, {
  UnitSliderItem,
} from "@/components/commons/sliders/UnitSlider.vue";
import Toggle, { ToggleItem, unitItems } from "@/components/commons/Toggle.vue";
import { fragilityCurve } from "@/utils/fragility";
import { UnitSystem } from "@/utils/unit";
import { getColorMap } from "@/utils/vuetify";
import { EChartsOption } from "echarts";
import { computed, reactive, ref } from "vue";
import { publicPath } from "@/utils/common";

type Material = "a36" | "a572";
interface Variables {
  l: number;
  db: number;
}

const parameters: UnitSliderItem<keyof Variables>[] = [
  {
    key: "l",
    label: "L",
    min: 1000,
    max: 12000,
    unit: "mm",
  },
  {
    key: "db",
    label: "d<sub>b</sub>",
    min: 100,
    max: 2000,
    unit: "mm",
  },
];
const materials: ToggleItem<Material>[] = [
  {
    value: "a36",
    text: "ASTM A36",
  },
  {
    value: "a572",
    text: "ASTM A572",
  },
];

const unitSystem = ref<UnitSystem>("metric");
const infoAvailable = ref(true);
const material = ref<Material>("a36");
const variables = reactive<Variables>({
  l: 4000,
  db: 600,
});

const preNorthridgeOption = computed<EChartsOption>(() => {
  let yieldingMedian: number;
  let yieldingSigma: number;
  let fractureMedian: number;
  let fractureSigma: number;
  if (infoAvailable.value) {
    yieldingMedian =
      material.value === "a36"
        ? Math.exp(-1.83 + 0.16 * (variables.l / variables.db))
        : Math.exp(-0.56 + 0.028 * (variables.l / variables.db));
    yieldingSigma = material.value === "a36" ? 0.24 : 0.18;
    fractureMedian = Math.exp(0.99 - 0.0074 * (variables.db / 10));
    fractureSigma = 0.44;
  } else {
    yieldingMedian = material.value === "a36" ? 0.77 : 0.76;
    yieldingSigma = material.value === "a36" ? 0.32 : 0.19;
    fractureMedian = 1.85;
    fractureSigma = 0.47;
  }
  return {
    xAxis: {
      name: "SDR",
    },
    yAxis: {
      name: "P(DS)",
    },
    color: getColorMap(2),
    series: [
      {
        type: "line",
        name: "Yielding",
        showSymbol: false,
        data: fragilityCurve(yieldingMedian, yieldingSigma),
      },
      {
        type: "line",
        name: "Brittle Fracture",
        showSymbol: false,
        data: fragilityCurve(fractureMedian, fractureSigma),
      },
    ],
  };
});

const postNorthridgeOption = computed<EChartsOption>(() => {
  return {
    xAxis: {
      name: "SDR",
    },
    yAxis: {
      name: "P(DS)",
    },
    color: getColorMap(5),
    series: [
      {
        type: "line",
        name: "Yielding Anywhere",
        showSymbol: false,
        data: fragilityCurve(1, 0.17),
      },
      {
        type: "line",
        name: "Yielding @ Panel Zone",
        showSymbol: false,
        data: fragilityCurve(1, 0.15),
      },
      {
        type: "line",
        name: "Yielding @ Flanges",
        showSymbol: false,
        data: fragilityCurve(0.96, 0.1),
      },
      {
        type: "line",
        name: "Local Buckling",
        showSymbol: false,
        data: fragilityCurve(2.16, 0.3),
      },
      {
        type: "line",
        name: "Ductile Tearing",
        showSymbol: false,
        data: fragilityCurve(5, 0.31),
      },
    ],
  };
});
</script>

<template>
  <v-row>
    <v-col cols="8">
      <h1>Fragility Curve Plotter for Steel Component</h1>
      <p>
        This tab introduces a web-based interactive module for visualizing
        fragility curves of Pre- and Post-Northridge beam-to-column connections.
        For further information refer to
        <a
          href="https://ascelibrary.org/doi/abs/10.1061/%28ASCE%29ST.1943-541X.0000214"
          >Lignos et al. (2010)</a
        >
        and
        <a
          href="https://www.sciencedirect.com/science/article/abs/pii/S0141029612003689"
          >Ramirez et al. (2012)</a
        >.
      </p>
    </v-col>
    <v-col cols="4" class="d-flex justify-end">
      <toggle v-model="unitSystem" :items="unitItems"></toggle>
    </v-col>
    <v-col cols="4">
      <v-card>
        <v-card-title>Select units</v-card-title>
        <v-card-text>
          <h2>Steel Type</h2>
          <toggle v-model="material" class="my-4" :items="materials"></toggle>
        </v-card-text>
        <v-card-text>
          <h2>Geometric Parameters</h2>
          <v-switch
            v-model="infoAvailable"
            color="primary"
            label="Geometric parameters available"
          ></v-switch>
          <unit-slider
            v-for="item in parameters"
            :key="item.key"
            v-model="variables[item.key]"
            class="my-4"
            :disabled="!infoAvailable"
            :label="item.label"
            :max="item.max"
            :min="item.min"
            :unit="item.unit"
            :unit-system="unitSystem"
          ></unit-slider>
        </v-card-text>
      </v-card>
      <v-col cols="12">
        <v-img
          contain
          height="300px"
          :src="publicPath + 'img/connection/connection_fragility.png'"
        ></v-img>
      </v-col>
    </v-col>
    <v-col cols="4">
      <h2>Pre-Northridge</h2>
      <unit-chart
        :option="preNorthridgeOption"
        :unit-system="unitSystem"
        x-unit="rad"
      ></unit-chart>
    </v-col>
    <v-col cols="4">
      <h2>Post-Northridge</h2>
      <unit-chart
        :option="postNorthridgeOption"
        :unit-system="unitSystem"
        x-unit="rad"
      ></unit-chart>
    </v-col>
  </v-row>
</template>
