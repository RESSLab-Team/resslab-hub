import cdf from "@stdlib/stats-base-dists-lognormal-cdf";
import { EChartsOption } from "echarts";
import { range } from "lodash";
import { colorPalette } from "./vuetify";

function storyDriftRatio(median: number): number[] {
  return range(0, median * 2.5, 0.01);
}

export function fragilityCurve(
  median: number,
  sigma: number,
  maxMedian = median
): [number, number][] {
  const sdr = storyDriftRatio(maxMedian);
  const medianLog = Math.log(median);
  return sdr.map((value) => [value, cdf(value, medianLog, sigma)]);
}

export interface DamageState {
  median: number;
  beta: number;
}

export function univariateOption(damageStates: DamageState[]): EChartsOption {
  const maxMedian = Math.max(...damageStates.map((state) => state.median));
  return {
    xAxis: {
      name: "SDR",
    },
    yAxis: {
      name: "P(DS)",
    },
    series: damageStates.map((state, index) => ({
      type: "line",
      name: `DS${index + 1}`,
      showSymbol: false,
      itemStyle: {
        color: colorPalette[index],
      },
      lineStyle: {
        color: colorPalette[index],
      },
      data: fragilityCurve(state.median, state.beta, maxMedian),
    })),
  };
}
