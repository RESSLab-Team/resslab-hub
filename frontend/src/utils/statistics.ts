import _ from "lodash";

export function toBins(counts: Count[], size?: number): Bin[] {
  const binSize = size ?? Math.ceil(Math.sqrt(counts.length));
  const roundedCounts: Count[] = counts.map((c) => ({
    value: Math.round(c.value),
    count: c.count,
  }));
  const values = roundedCounts.map((c) => c.value);
  const globalMin = Math.min(...values);
  const globalMax = Math.max(...values);
  if (globalMin === globalMax) {
    return [
      [
        `${globalMin}`,
        _.sumBy(roundedCounts, (c) => c.count),
        globalMin,
        globalMax,
      ],
    ];
  }
  return _.range(globalMin, globalMax, binSize).map((min) => {
    const max = Math.min(min + binSize, globalMax + 1) - 1;
    const totalCount = _(roundedCounts)
      .filter((c) => min <= c.value && c.value <= max)
      .sumBy((c) => c.count);
    return [min < max ? `${min}-${max}` : `${min}`, totalCount, min, max];
  });
}

export interface Count {
  value: number;
  count: number;
}

export type Bin = [
  string, // label
  number, // count
  number, // min
  number // max
];
