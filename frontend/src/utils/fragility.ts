import cdf from "@stdlib/stats-base-dists-lognormal-cdf";
import { range } from "lodash";

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
