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
import { UnitSystem } from "@/utils/unit";
import cdf from "@stdlib/stats-base-dists-lognormal-cdf";
import { EChartsOption } from "echarts/types/dist/shared";
import { range } from "lodash";
import { Component, Vue } from "vue-property-decorator";
import { colors } from "vuetify/lib";

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

  storyDriftRatio(median: number): number[] {
    return range(0, median * 2.5, 0.01);
  }

  fragilityCurve(median: number, sigma: number): [number, number][] {
    const sdr = this.storyDriftRatio(median);
    const medianLog = Math.log(median);
    return sdr.map((value) => [value, cdf(value, medianLog, sigma)]);
  }

  get postNorthridgeOption(): EChartsOption {
    return {
      xAxis: {
        name: "SDR",
      },
      yAxis: {
        name: "P(DS)",
      },
      series: [
        {
          type: "line",
          name: "Yielding Anywhere",
          color: colors.shades.black,
          showSymbol: false,
          data: this.fragilityCurve(1, 0.17),
        },
        {
          type: "line",
          name: "Yielding @ Panel Zone",
          color: colors.red.base,
          showSymbol: false,
          data: this.fragilityCurve(1, 0.15),
        },
        {
          type: "line",
          name: "Yielding @ Flanges",
          color: colors.green.base,
          showSymbol: false,
          data: this.fragilityCurve(0.96, 0.1),
        },
        {
          type: "line",
          name: "Local Buckling",
          color: colors.deepPurple.base,
          showSymbol: false,
          data: this.fragilityCurve(2.16, 0.3),
        },
        {
          type: "line",
          name: "Ductile Tearing",
          color: colors.blue.base,
          showSymbol: false,
          data: this.fragilityCurve(5, 0.31),
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
      series: [
        {
          type: "line",
          name: "Yielding",
          color: colors.shades.black,
          showSymbol: false,
          data: this.fragilityCurve(yieldingMedian, yieldingSigma),
        },
        {
          type: "line",
          name: "Brittle Fracture",
          color: colors.red.base,
          showSymbol: false,
          data: this.fragilityCurve(fractureMedian, fractureSigma),
        },
      ],
    };
  }
}

type Material = "a36" | "a572";
</script>
