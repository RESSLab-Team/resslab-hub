<template>
  <v-row>
    <v-col cols="12">
      <h1>Fragility Curve Plotter for Steel Component</h1>
    </v-col>
    <v-col cols="12">
      <v-card>
        <v-card-title>Select Material</v-card-title>
        <v-card-text>
          <v-row>
            <v-col>
              <h2>Steel Type</h2>
              <toggle
                v-model="material"
                class="my-4"
                :items="materials"
              ></toggle>
            </v-col>
            <v-col>
              <h2>Geometric Parameters</h2>
              <unit-slider
                v-for="item in parameters"
                :key="item.key"
                v-model="$data[item.key]"
                class="my-4"
                :label="item.label"
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
    <v-col cols="6">
      <h2>Post-Northridge</h2>
      <unit-chart :option="postNorthridgeOption" x-unit="rad"></unit-chart>
    </v-col>
    <v-col cols="6">
      <h2>Pre-Northridge</h2>
      <unit-chart :option="preNorthridgeOption" x-unit="rad"></unit-chart>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import UnitChart from "@/components/commons/charts/UnitChart.vue";
import UnitSlider, {
  UnitSliderItem,
} from "@/components/commons/sliders/UnitSlider.vue";
import Toggle, { ToggleItem } from "@/components/commons/Toggle.vue";
import { fragilityCurve } from "@/utils/fragility";
import { UnitSystem } from "@/utils/unit";
import { colorPalette } from "@/utils/vuetify";
import { EChartsOption } from "echarts";
import { Component, Vue } from "vue-property-decorator";

@Component({
  components: {
    Toggle,
    UnitSlider,
    UnitChart,
  },
})
export default class ConnectionFragility extends Vue {
  readonly unitSystem: UnitSystem = "metric";

  readonly parameters: UnitSliderItem<keyof ConnectionFragility>[] = [
    {
      key: "l",
      label: "L",
      min: 1000,
      max: 12000,
    },
    {
      key: "db",
      label: "d<sub>b</sub>",
      min: 100,
      max: 2000,
    },
  ];

  material: Material = "a36";
  materials: ToggleItem<Material>[] = [
    {
      value: "a36",
      text: "ASTM A36",
    },
    {
      value: "a572",
      text: "ASTM A572",
    },
  ];

  l = 4000;
  db = 600;

  get postNorthridgeOption(): EChartsOption {
    return {
      xAxis: {
        name: "SDR",
      },
      yAxis: {
        name: "P(DS)",
      },
      color: colorPalette,
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
  }

  get preNorthridgeOption(): EChartsOption {
    const yieldingMedian = this.material === "a36" ? 0.77 : 0.76;
    const yieldingSigma = this.material === "a36" ? 0.32 : 0.19;
    const fractureMedian = 1.85;
    const fractureSigma = 0.47;
    return {
      xAxis: {
        name: "SDR",
      },
      yAxis: {
        name: "P(DS)",
      },
      color: colorPalette,
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
  }
}

type Material = "a36" | "a572";
</script>
