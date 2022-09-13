<template>
  <v-row>
    <v-col cols="12">
      <h1>Fragility Curve Plotter</h1>
    </v-col>
    <v-col cols="6">
      <h2>Univariate Fragility Curves</h2>
      <v-row>
        <v-col cols="6">
          <h3>Square HSS Braces</h3>
          <unit-chart
            :option="univariateOptions['square-hss']"
            x-unit="rad"
          ></unit-chart>
        </v-col>
        <v-col cols="6">
          <h3>Round HSS Braces</h3>
          <unit-chart
            :option="univariateOptions['round-hss']"
            x-unit="rad"
          ></unit-chart>
        </v-col>
        <v-col cols="6">
          <h3>Wide-Flange Braces</h3>
          <unit-chart
            :option="univariateOptions['w-shape']"
            x-unit="rad"
          ></unit-chart>
        </v-col>
        <v-col cols="6">
          <h3>Angle (L-shape) Braces</h3>
          <unit-chart
            :option="univariateOptions['l-shape']"
            x-unit="rad"
          ></unit-chart>
        </v-col>
      </v-row>
    </v-col>
    <v-col cols="6">
      <h2>Multivariate Fragility Curves</h2>
      <toggle v-model="option" :items="options"></toggle>
      <v-row>
        <v-col
          v-for="(item, index) in multivariateOptions"
          :key="index"
          cols="6"
        >
          <surface-gl-chart :option="item"></surface-gl-chart>
        </v-col>
      </v-row>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import SurfaceGlChart from "@/components/commons/charts/SurfaceGlChart.vue";
import UnitChart from "@/components/commons/charts/UnitChart.vue";
import UnitSlider from "@/components/commons/sliders/UnitSlider.vue";
import Toggle, { ToggleItem } from "@/components/commons/Toggle.vue";
import { EChartsGlOption } from "@/utils/echarts-gl";
import { DamageState, univariateOption } from "@/utils/fragility";
import { subscripts } from "@/utils/unicode";
import { UnitSystem } from "@/utils/unit";
import cdf from "@stdlib/stats-base-dists-lognormal-cdf";
import { EChartsOption } from "echarts";
import { range, zip } from "lodash";
import { index, Matrix, matrix, max, sum } from "mathjs";
import { Component, Vue } from "vue-property-decorator";

/**
 * Computations from https://github.com/RESSLab-Team/resslab-hub-scripts/tree/main/fragility_curves_steel_braces
 */
@Component({
  components: {
    SurfaceGlChart,
    Toggle,
    UnitSlider,
    UnitChart,
  },
})
export default class BraceFragility extends Vue {
  readonly unitSystem: UnitSystem = "metric";
  readonly damageStates: Record<Option, DamageState[]> = {
    "square-hss": [
      {
        median: 0.4,
        beta: 0.43,
      },
      {
        median: 1.02,
        beta: 0.44,
      },
      {
        median: 1.6,
        beta: 0.48,
      },
    ],
    "round-hss": [
      {
        median: 0.4,
        beta: 0.43,
      },
      {
        median: 1.02,
        beta: 0.44,
      },
      {
        median: 1.6,
        beta: 0.48,
      },
    ],
    "w-shape": [
      {
        median: 0.3,
        beta: 0.58,
      },
      {
        median: 1.01,
        beta: 0.54,
      },
      {
        median: 3.1,
        beta: 0.41,
      },
    ],
    "l-shape": [
      {
        median: 0.27,
        beta: 0.51,
      },
      {
        median: 0.7,
        beta: 0.65,
      },
      {
        median: 1.43,
        beta: 0.52,
      },
    ],
  };
  readonly options: ToggleItem<Option>[] = [
    {
      value: "square-hss",
      text: "Square HSS",
    },
    {
      value: "round-hss",
      text: "Round HSS",
    },
    {
      value: "w-shape",
      text: "Wide-Flange",
    },
    {
      value: "l-shape",
      text: "Angle (L-shape)",
    },
  ];
  /**
   * Global slenderness KL/r
   */
  readonly slendernesses: Record<Option, DamageState[]> = {
    "square-hss": [
      {
        median: 62.8,
        beta: 0.33,
      },
      {
        median: 62.5,
        beta: 0.33,
      },
      {
        median: 62.3,
        beta: 0.35,
      },
    ],
    "round-hss": [
      {
        median: 63.6,
        beta: 0.46,
      },
      {
        median: 66.1,
        beta: 0.45,
      },
      {
        median: 68.9,
        beta: 0.4,
      },
    ],
    "w-shape": [
      {
        median: 62.9,
        beta: 0.47,
      },
      {
        median: 64.5,
        beta: 0.45,
      },
      {
        median: 72.3,
        beta: 0.37,
      },
    ],
    "l-shape": [
      {
        median: 76.8,
        beta: 0.45,
      },
      {
        median: 81.5,
        beta: 0.44,
      },
      {
        median: 97.3,
        beta: 0.39,
      },
    ],
  };

  option: Option = "square-hss";

  get univariateOptions(): Record<Option, EChartsOption> {
    return Object.fromEntries(
      Object.entries(this.damageStates).map(([key, value]) => [
        key,
        univariateOption(value),
      ])
    ) as Record<Option, EChartsOption>;
  }

  get multivariateOptions(): EChartsGlOption[] {
    return zip(this.damageStates[this.option], this.slendernesses[this.option])
      .filter(
        (item): item is [DamageState, DamageState] =>
          item[0] !== undefined && item[1] !== undefined
      )
      .map(([ds, kl], index) =>
        this.correlatedBivariateOption(ds, kl, (index + 1).toString())
      );
  }

  correlatedBivariateOption(
    ds: DamageState,
    kl: DamageState,
    name: string
  ): EChartsGlOption {
    return {
      xAxis3D: {
        name: "SDR [rad]",
      },
      yAxis3D: {
        name: "KL/r",
      },
      zAxis3D: {
        name: `P(DS${subscripts[name]}|SDR,KL/r)`,
      },
      series: [
        {
          type: "surface",
          data: this.correlatedBivariate(
            range(0.0001, 0.05, 0.005),
            range(10, 105, 5),
            ds,
            kl
          ),
        },
      ],
    };
  }

  correlatedBivariate(
    xs: number[],
    ys: number[],
    ds: DamageState,
    kl: DamageState,
    corr = 0
  ): [number, number, number][] {
    const median1 = ds.median / 100;
    const median2 = kl.median;
    const sigma1 = ds.beta;
    const sigma2 = kl.beta;
    const muln1 = Math.log(median1) - Math.pow(sigma1, 2) / 2;
    const muln2 = Math.log(median2) - Math.pow(sigma2, 2) / 2;

    const pdfMatrix: Matrix = matrix();
    for (let i = 0; i < xs.length; i++) {
      const x = xs[i];
      const a1 = Math.log(x) - muln1;
      for (let j = 0; j < ys.length; j++) {
        const y = ys[j];
        const a2 = Math.log(y) - muln2;
        const q =
          (1 / (1 - Math.pow(corr, 2))) *
          (Math.pow(a1, 2) / Math.pow(sigma1, 2) -
            (2 * corr * a1 * a2) / (sigma1 * sigma2) +
            Math.pow(a2, 2) / Math.pow(sigma2, 2));
        pdfMatrix.set(
          [i, j],
          (1 /
            (2 *
              Math.PI *
              x *
              y *
              sigma1 *
              sigma2 *
              Math.pow(1 - Math.pow(corr, 2), 0.5))) *
            Math.exp(-q / 2)
        );
      }
    }

    let cdfMatrix: Matrix = matrix();
    const allIRange = range(0, xs.length);
    const allJRange = range(0, ys.length);
    for (let i = 0; i < xs.length; i++) {
      const iRange = range(0, i + 1);
      const sum2 = sum(pdfMatrix.subset(index(iRange, allJRange)));
      for (let j = 0; j < ys.length; j++) {
        const jRange = range(0, j + 1);
        const sum3 = sum(pdfMatrix.subset(index(iRange, jRange)));
        const sum1 = sum(pdfMatrix.subset(index(allIRange, jRange)));
        cdfMatrix.set([i, j], sum1 + sum2 - sum3);
      }
    }

    cdfMatrix = cdfMatrix.map((value, index) => {
      const i = index as unknown as [number, number];
      return (
        value * cdf(xs[i[0]], muln1, sigma1) * cdf(ys[i[1]], muln2, sigma2)
      );
    });

    const maxValue = max(cdfMatrix);
    cdfMatrix = cdfMatrix.map((v) => v / maxValue);

    const data: [number, number, number][] = [];
    for (let i = 0; i < xs.length; i++) {
      for (let j = 0; j < ys.length; j++) {
        data.push([xs[i], ys[j], cdfMatrix.get([i, j])]);
      }
    }
    return data;
  }
}

type Option = "square-hss" | "round-hss" | "w-shape" | "l-shape";
</script>
