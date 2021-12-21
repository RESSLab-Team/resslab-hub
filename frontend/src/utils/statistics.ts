import { bin } from "d3-array";

export function toBins(names: string[], counts: Count[]): Bin[] {
  const values = counts.flatMap((c) =>
    Array(c.count).fill({ name: c.name, value: c.value })
  );
  const bins = bin<{ name: string; value: number }, number>().value(
    (d) => d.value
  )(values);
  return names.map((name) => ({
    name: name,
    data: bins.map((bin) => {
      const min: number = bin.x0 ?? Number.MIN_SAFE_INTEGER;
      const max: number = bin.x1 ?? Number.MAX_SAFE_INTEGER;
      const count = bin.filter((b) => b.name === name).length;
      return [`${min}-${max}`, count > 0 ? count : "", min, max];
    }),
  }));
}

export interface Count {
  name: string;
  value: number;
  count: number;
}

export interface Bin {
  name: string;
  data: BinData[];
}

export type BinData = [
  string, // label
  number | string, // count
  number, // min
  number // max
];
