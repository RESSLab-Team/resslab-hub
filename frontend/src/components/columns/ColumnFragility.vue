<script setup lang="ts">
// Computations from https://github.com/RESSLab-Team/resslab-hub-scripts/tree/main/fragility_curves_steel_columns
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
import { computed, reactive, ref } from "vue";
import TitleRow from "@/components/commons/TitleRow.vue";
const parameters: UnitSliderItem<keyof Variables>[] = [
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
const alphas: number[] = [5.515, 10.753, 14.664, 16.659];
const maxSdr = 11.01;
const sdr = range(0, maxSdr, 0.01);

interface Variables {
  hTw: number;
  pPyn: number;
}
const variables = reactive<Variables>({
  hTw: 40,
  pPyn: 0.2,
});

const alphaColorPalette = getColorMap(alphas.length);
const legendItems = ref([
  ...alphas.map((_, index) => ({
    label: `DS${index + 1}`,
    indexToFilter: index,
    color: alphaColorPalette[index],
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
]);
const indexSelected = computed<number[]>(() =>
  legendItems.value
    .filter((d) => d.indexToFilter >= 0 && d.selected)
    .map((d) => d.indexToFilter)
);
const univariateSelected = computed<boolean>(
  () =>
    legendItems.value.find((d) => d.label === "Univariate")?.selected || false
);
const multivariateSelected = computed<boolean>(
  () =>
    legendItems.value.find((d) => d.label === "Multivariate")?.selected || false
);
const variateOption = computed<EChartsOption>(() => {
  const series: SeriesOption[] = [];
  if (univariateSelected.value) {
    const option = univariateOption(
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
      maxSdr,
      "Univariate "
    );
    const selectedUnivariateSeries: SeriesOption[] = (
      option.series as SeriesOption[]
    ).filter((_, index) => indexSelected.value.includes(index));
    if (selectedUnivariateSeries.length > 0) {
      series.push(...selectedUnivariateSeries);
    }
  }
  if (multivariateSelected.value) {
    const option = {
      xAxis: {
        name: "SDR",
      },
      yAxis: {
        name: "P(DS≥ds)",
      },
      series: alphas.map((alpha, index) => ({
        type: "line",
        name: `Multivariate P(DS≥ds${subscripts[(index + 1).toString()]})`,
        showSymbol: false,
        animation: false,
        itemStyle: {
          color: alphaColorPalette[index],
        },
        lineStyle: {
          color: alphaColorPalette[index],
          type: "dotted",
        },
        data: sdr.map((item) => [
          item,
          surface(variables.hTw, item, alpha, variables.pPyn),
        ]),
      })),
    };
    const selectedMultivariateSeries: SeriesOption[] = (
      option.series as SeriesOption[]
    ).filter((_, index) => indexSelected.value.includes(index));
    if (selectedMultivariateSeries.length > 0) {
      series.push(...selectedMultivariateSeries);
    }
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
  } as EChartsOption;
});
const surfaceOptions = computed<EChartsGlOption[]>(() =>
  alphas.map((alpha, index) =>
    getSurfaceOption(
      (index + 1).toString(),
      alpha,
      variables.hTw,
      variables.pPyn,
      alphaColorPalette[index]
    )
  )
);

function getSurfaceOption(
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
            return surface(x, y, alpha, pPyn);
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

function surface(
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
</script>

<template>
  <div>
    <v-row>
      <v-col cols="12">
        <title-row :show-unit-toggle="false">
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
        </title-row>
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
                      v-model="variables[item.key]"
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
