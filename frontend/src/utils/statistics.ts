import { bin } from 'd3-array'

export function toBins(names: string[], counts: Count[]): Bin[] {
  // Bin the aggregated counts directly instead of re-expanding them into one
  // object per underlying observation (`Array(c.count).fill(...)`), which scaled
  // with the total row count on every recompute. d3's default bin count is
  // Sturges' rule over the *expanded* sample size, so we replicate that
  // threshold count explicitly from the total n and then sum `count` per bin —
  // producing identical bins/labels without materialising the rows.
  const n = counts.reduce((total, c) => total + c.count, 0)
  const sturges = Math.max(1, Math.ceil(Math.log2(Math.max(1, n))) + 1)
  const bins = bin<Count, number>()
    .value((d) => d.value)
    .thresholds(sturges)(counts)
  return names.map((name) => ({
    name: name,
    data: bins.map((bin) => {
      const min: number = bin.x0 ?? Number.MIN_SAFE_INTEGER
      const max: number = bin.x1 ?? Number.MAX_SAFE_INTEGER
      const count = bin.reduce((total, b) => (b.name === name ? total + b.count : total), 0)
      return [`${min}-${max}`, count > 0 ? count : '', min, max]
    })
  }))
}

export interface Count {
  name: string
  value: number
  count: number
}

export interface Bin {
  name: string
  data: BinData[]
}

export type BinData = [
  string, // label
  number | string, // count
  number, // min
  number // max
]
