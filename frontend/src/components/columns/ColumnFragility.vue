<template>
  <v-row>
    <v-col cols="12">
      <h1>Fragility Curve Plotter</h1>
    </v-col>
    <v-col cols="12">
      <v-card>
        <v-card-title>Parameters</v-card-title>
        <v-card-text>
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
        </v-card-text>
      </v-card>
    </v-col>
    <v-col cols="6">
      <v-row>
        <v-col cols="6">
          <h2>Univariate Fragility Curves</h2>
          <unit-chart :option="univariateOption" x-unit="rad"></unit-chart>
        </v-col>
        <v-col cols="6">
          <h2>Multivariate Fragility Curves</h2>
          <unit-chart :option="multivariateOption" x-unit="rad"></unit-chart>
        </v-col>
        <v-col cols="6">
          <h2>Fragility Curves</h2>
          <unit-chart :option="variateOption" x-unit="rad"></unit-chart>
        </v-col>
      </v-row>
    </v-col>
    <v-col cols="6">
      <h2>Surface Fragility Curves</h2>
      <v-row>
        <v-col cols="6">
          <surface-gl-chart :option="surfaceOptions[0]"></surface-gl-chart>
        </v-col>
        <v-col cols="6">
          <surface-gl-chart :option="surfaceOptions[1]"></surface-gl-chart>
        </v-col>
        <v-col cols="6">
          <surface-gl-chart :option="surfaceOptions[2]"></surface-gl-chart>
        </v-col>
        <v-col cols="6">
          <surface-gl-chart :option="surfaceOptions[3]"></surface-gl-chart>
        </v-col>
      </v-row>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import SurfaceGlChart from "@/components/commons/charts/SurfaceGlChart.vue";
import UnitChart from "@/components/commons/charts/UnitChart.vue";
import UnitSlider, {
  UnitSliderItem,
} from "@/components/commons/sliders/UnitSlider.vue";
import { EChartsGlOption } from "@/utils/echarts-gl";
import { univariateOption } from "@/utils/fragility";
import { subscripts } from "@/utils/unicode";
import { UnitSystem } from "@/utils/unit";
import { colorPalette } from "@/utils/vuetify";
import { EChartsOption, SeriesOption } from "echarts";
import { range } from "lodash";
import { Component, Vue } from "vue-property-decorator";

/**
 * Computations from https://github.com/RESSLab-Team/resslab-hub-scripts/tree/main/fragility_curves_steel_columns
 */
@Component({
  components: {
    SurfaceGlChart,
    UnitSlider,
    UnitChart,
  },
})
export default class ColumnFragility extends Vue {
  readonly unitSystem: UnitSystem = "metric";

  readonly parameters: UnitSliderItem<keyof ColumnFragility>[] = [
    {
      key: "hTw",
      label: "h / tw",
      min: 5,
      max: 60,
    },
    {
      key: "pPyn",
      label: "p / pyn",
      min: 0,
      max: 1,
    },
  ];
  readonly alphas: number[] = [5.515, 10.753, 14.664, 16.659];
  readonly sdr = range(0, 11, 0.01);

  hTw = 40;
  pPyn = 0.2;

  get univariateOption(): EChartsOption {
    return univariateOption([
      {
        median: 0.507,
        beta: 0.425,
      },
      {
        median: 1.368,
        beta: 0.552,
      },
      {
        median: 2.292,
        beta: 0.491,
      },
      {
        median: 3.502,
        beta: 0.321,
      },
      {
        median: 4.336,
        beta: 0.327,
      },
    ]);
  }

  get multivariateOption(): EChartsOption {
    return {
      xAxis: {
        name: "SDR",
      },
      yAxis: {
        name: "P(DS\u2265ds)",
      },
      color: colorPalette,
      series: this.alphas.map((alpha, index) => ({
        type: "line",
        name: `P(DS\u2265ds${subscripts[(index + 1).toString()]})`,
        showSymbol: false,
        itemStyle: {
          color: colorPalette[index],
        },
        lineStyle: {
          color: colorPalette[index],
          type: "dotted",
        },
        data: this.sdr.map((item) => [
          item,
          ColumnFragility.surface(this.hTw, item, alpha, this.pPyn),
        ]),
      })),
    };
  }

  get variateOption(): EChartsOption {
    return {
      xAxis: {
        name: "SDR",
      },
      yAxis: {
        name: "P(DS)",
      },
      series: [
        ...((this.univariateOption.series as SeriesOption[]) ?? []),
        ...((this.multivariateOption.series as SeriesOption[]) ?? []),
      ],
    };
  }

  get surfaceOptions(): EChartsGlOption[] {
    return this.alphas.map((alpha, index) =>
      ColumnFragility.getSurfaceOption(
        (index + 1).toString(),
        alpha,
        this.hTw,
        this.pPyn,
        colorPalette[index]
      )
    );
  }

  static getSurfaceOption(
    name: string,
    alpha: number,
    hTw: number,
    pPyn: number,
    color: string
  ): EChartsGlOption {
    const yMin = 0;
    const yMax = 7;
    const zMin = 0;
    const zMax = 1;
    return {
      xAxis3D: {
        name: "h/tw",
      },
      yAxis3D: {
        name: "SDR [% rad]",
      },
      zAxis3D: {
        name: `P(DS${subscripts[name]}|SDR)`,
      },
      series: [
        {
          type: "surface",
          wireframe: {
            show: false,
          },
          equation: {
            x: {
              min: 0,
              max: 60,
              step: 1,
            },
            y: {
              min: yMin,
              max: yMax,
              step: 0.1,
            },
            z: (x: number, y: number) => {
              return this.surface(x, y, alpha, pPyn);
            },
          },
          itemStyle: {
            color,
          },
        },
        {
          type: "surface",
          itemStyle: {
            color: "black",
            opacity: 0.5,
          },
          data: [
            [hTw, yMin, zMin],
            [hTw, yMin, zMax],
            [hTw, yMax, zMin],
            [hTw, yMax, zMax],
          ],
        },
      ],
    };
  }

  static surface(
    hTw: number,
    sdr: number,
    alpha: number,
    pPyn: number
  ): number {
    const betaHtw = -0.15;
    const betaPpy = -11.081;
    const betaSdr = -5.708;
    const y = alpha + betaHtw * hTw + betaPpy * pPyn + betaSdr * Math.log(sdr);
    return 1 - Math.exp(y) / (1 + Math.exp(y));
  }
}
</script>
