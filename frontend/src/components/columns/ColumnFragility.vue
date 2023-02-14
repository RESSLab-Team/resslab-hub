<template>
  <div>
    <v-row>
      <v-col cols="12">
        <h1>Fragility Curve Plotter for Wide-Flange Steel Columns</h1>
        <p>
          This module plots univariate and multivariate fragility curves for
          wide-flange steel columns depending on their primary loading and
          geometric characteristics. For further information please refer to
          <a
            href="https://journals.sagepub.com/doi/abs/10.1193/122017EQS260M?journalCode=eqsa"
            >Elkady et al. (2018)</a
          >.
        </p>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="6">
        <v-row>
          <v-col cols="12">
            <v-card>
              <v-card-title>
                Parameters
                <info-tooltip>
                  Please provide the imposed gravity-induced axial load ratio,
                  Pg/Pyn and the web slenderness ratio, h/tw of the wide-flange
                  cross section of the steel column.
                </info-tooltip>
              </v-card-title>
              <v-card-text>
                <v-row>
                  <v-col v-for="item in parameters" :key="item.key">
                    <unit-slider
                      v-model="$data[item.key]"
                      :label="item.label"
                      :max="item.max"
                      :min="item.min"
                      :unit="item.unit"
                    />
                  </v-col>
                </v-row>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
        <v-row>
          <v-col cols="12">
            <h2>Fragility Curves</h2>
            <v-row>
              <v-col cols="9">
                <unit-chart
                  :aspect-ratio="2"
                  :option="variateOption"
                  x-unit="rad"
                />
              </v-col>
              <v-col cols="3">
                <legend-chart v-model="legendItems" :separators-index="[4]" />
              </v-col>
            </v-row>
          </v-col>
        </v-row>
      </v-col>
      <v-col cols="6">
        <h2>Surface Fragility Curves</h2>
        <v-row>
          <v-col v-for="(item, index) in surfaceOptions" :key="index" cols="6">
            <surface-gl-chart :option="item" />
          </v-col>
        </v-row>
      </v-col>
    </v-row>
  </div>
</template>

<script lang="ts">
import LegendChart from "@/components/commons/charts/LegendChart.vue";
import SurfaceGlChart from "@/components/commons/charts/SurfaceGlChart.vue";
import UnitChart from "@/components/commons/charts/UnitChart.vue";
import InfoTooltip from "@/components/commons/InfoTooltip.vue";
import UnitSlider, {
  UnitSliderItem,
} from "@/components/commons/sliders/UnitSlider.vue";
import { EChartsGlOption } from "@/utils/echarts-gl";
import { univariateOption } from "@/utils/fragility";
import { subscripts } from "@/utils/unicode";
import { getColorMap } from "@/utils/vuetify";
import { EChartsOption, SeriesOption } from "echarts";
import { range } from "lodash";
import { Component, Vue } from "vue-property-decorator";

/**
 * Computations from https://github.com/RESSLab-Team/resslab-hub-scripts/tree/main/fragility_curves_steel_columns
 */
@Component({
  components: {
    LegendChart,
    InfoTooltip,
    SurfaceGlChart,
    UnitSlider,
    UnitChart,
  },
})
export default class ColumnFragility extends Vue {
  readonly parameters: UnitSliderItem<keyof ColumnFragility>[] = [
    {
      key: "hTw",
      label: "h / tw",
      min: 5,
      max: 60,
    },
    {
      key: "pPyn",
      label: "Pg / Pyn",
      min: 0,
      max: 1,
    },
  ];
  readonly alphas: number[] = [5.515, 10.753, 14.664, 16.659];
  readonly maxSdr = 11.01;
  readonly sdr = range(0, this.maxSdr, 0.01);

  hTw = 40;
  pPyn = 0.2;

  legendItems = [
    ...this.alphas.map((_, index) => ({
      label: `DS${index + 1}`,
      indexToFilter: index,
      color: this.alphaColorPalette[index],
      icon: "mdi-rectangle",
      selected: true,
    })),
    {
      label: "Univariate",
      color: "black",
      icon: "mdi-rectangle",
      selected: true,
      indexToFilter: -1,
    },
    {
      label: "Multivariate",
      color: "black",
      icon: "mdi-dots-horizontal",
      selected: true,
      indexToFilter: -1,
    },
  ];

  get indexSelected(): number[] {
    return this.legendItems
      .filter((d) => d.indexToFilter >= 0 && d.selected)
      .map((d) => d.indexToFilter);
  }

  get univariateSelected(): boolean {
    return (
      this.legendItems.find((d) => d.label === "Univariate")?.selected || false
    );
  }

  get multivariateSelected(): boolean {
    return (
      this.legendItems.find((d) => d.label === "Multivariate")?.selected ||
      false
    );
  }

  get univariateOption(): EChartsOption {
    return univariateOption(
      [
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
      ],
      this.maxSdr,
      "Univariate "
    );
  }

  get alphaColorPalette(): string[] {
    return getColorMap(this.alphas.length);
  }

  get multivariateOption(): EChartsOption {
    return {
      xAxis: {
        name: "SDR",
      },
      yAxis: {
        name: "P(DS≥ds)",
      },
      series: this.alphas.map((alpha, index) => ({
        type: "line",
        name: `Multivariate P(DS≥ds${subscripts[(index + 1).toString()]})`,
        showSymbol: false,
        animation: false,
        itemStyle: {
          color: this.alphaColorPalette[index],
        },
        lineStyle: {
          color: this.alphaColorPalette[index],
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
    const series = [];
    if (this.univariateSelected) {
      const univariateSeries = this.univariateOption.series as SeriesOption[],
        selectedUnivariateSeries = univariateSeries.filter((serie, index) =>
          this.indexSelected.includes(index)
        );
      series.push(...(selectedUnivariateSeries ?? []));
    }
    if (this.multivariateSelected) {
      const multivariateSeries = this.multivariateOption
          .series as SeriesOption[],
        selectedMultivariateSeries = multivariateSeries.filter((serie, index) =>
          this.indexSelected.includes(index)
        );
      series.push(...(selectedMultivariateSeries ?? []));
    }

    return {
      xAxis: {
        name: "SDR",
      },
      yAxis: {
        name: "P(DS)",
      },
      legend: {
        show: false,
      },

      series,
    };
  }

  get surfaceOptions(): EChartsGlOption[] {
    return this.alphas.map((alpha, index) =>
      ColumnFragility.getSurfaceOption(
        (index + 1).toString(),
        alpha,
        this.hTw,
        this.pPyn,
        this.alphaColorPalette[index]
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
        nameTextStyle: {
          fontSize: 14,
        },
      },
      yAxis3D: {
        name: "SDR [% rad]",
        nameTextStyle: {
          fontSize: 14,
        },
      },
      zAxis3D: {
        name: `P(DS${name})`,
        nameTextStyle: {
          fontSize: 14,
        },
      },
      series: [
        {
          type: "surface",
          name: "",
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
          name: "",
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
          silent: true,
          dataShape: [2, 2],
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
