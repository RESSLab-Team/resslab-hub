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
              <toggle v-model="unitSystem" :items="unitItems"></toggle>
              <br />
              <br />
              <h2>Steel Type</h2>
              <toggle
                v-model="material"
                class="my-4"
                :items="materials"
              ></toggle>
            </v-col>
            <v-col>
              <h2>Geometric Parameters</h2>
              <v-switch
                v-model="infoAvailable"
                color="blue"
                label="Geometric parameters available"
              ></v-switch>
              <unit-slider
                v-for="item in parameters"
                :key="item.key"
                v-model="$data[item.key]"
                class="my-4"
                :disabled="!infoAvailable"
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
      <h2>Pre-Northridge</h2>
      <unit-chart
        :option="preNorthridgeOption"
        :unit-system="unitSystem"
        x-unit="rad"
      ></unit-chart>
    </v-col>
    <v-col cols="6">
      <h2>Post-Northridge</h2>
      <unit-chart
        :option="postNorthridgeOption"
        :unit-system="unitSystem"
        x-unit="rad"
      ></unit-chart>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import UnitChart from "@/components/commons/charts/UnitChart.vue";
import UnitSlider, {
  UnitSliderItem,
} from "@/components/commons/sliders/UnitSlider.vue";
import Toggle, { ToggleItem, unitItems } from "@/components/commons/Toggle.vue";
import { fragilityCurve } from "@/utils/fragility";
import { UnitSystem } from "@/utils/unit";
import { getColorMap } from "@/utils/vuetify";
import { EChartsOption } from "echarts";
import { Component, Vue } from "vue-property-decorator";

/**
 * Computations from https://github.com/RESSLab-Team/resslab-hub-scripts/tree/main/fragility_curves_steel_connections
 */
@Component({
  components: {
    Toggle,
    UnitChart,
    UnitSlider,
  },
})
export default class ConnectionFragility extends Vue {
  readonly unitItems = unitItems;
  readonly unitSystem: UnitSystem = "metric";

  readonly parameters: UnitSliderItem<keyof ConnectionFragility>[] = [
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

  infoAvailable = true;
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

  get preNorthridgeOption(): EChartsOption {
    let yieldingMedian: number;
    let yieldingSigma: number;
    let fractureMedian: number;
    let fractureSigma: number;
    if (this.infoAvailable) {
      yieldingMedian =
        this.material === "a36"
          ? Math.exp(-1.83 + 0.16 * (this.l / this.db))
          : Math.exp(-0.56 + 0.028 * (this.l / this.db));
      yieldingSigma = this.material === "a36" ? 0.24 : 0.18;
      fractureMedian = Math.exp(0.99 - 0.0074 * (this.db / 10));
      fractureSigma = 0.44;
    } else {
      yieldingMedian = this.material === "a36" ? 0.77 : 0.76;
      yieldingSigma = this.material === "a36" ? 0.32 : 0.19;
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
  }

  get postNorthridgeOption(): EChartsOption {
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
  }
}

type Material = "a36" | "a572";
</script>
