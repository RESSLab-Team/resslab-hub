/**
 * The counts a filter shows once other filters are active (#329).
 *
 * `profileColumns` classifies the columns once, over the whole dataset, and that
 * result never changes. This module only counts one column again over the rows
 * that pass the other filters, and lays the result over the static descriptor.
 * The caller decides which rows: see `countsFor` in composables/useAutoFilters.ts.
 *
 * The list keeps its static order and its static values, zeros included, so a
 * list does not jump under the pointer and a value can be picked before the
 * filter that hides it is loosened.
 */
import { type FilterDescriptor, type FilterOption } from './filterProfile'
import { cellKey, type Row } from './queryEngine'
import type { BinData } from './statistics'

export interface LiveOption extends FilterOption {
  /** The count over the whole dataset. `count` is the count over the given rows. */
  total: number
}

export interface LiveCounts {
  /** categorical, boolean, date. */
  options?: LiveOption[]
  /** numeric. */
  bins?: BinData[]
}

/** The counts of the whole dataset: nothing to count again. */
export function staticCounts(filter: FilterDescriptor): LiveCounts {
  return {
    options: filter.options?.map((option) => ({ ...option, total: option.count })),
    bins: filter.bins
  }
}

/** One column counted over `rows`, in the shape its kind of filter reads. */
export function liveCounts(rows: Row[], filter: FilterDescriptor): LiveCounts {
  switch (filter.kind) {
    case 'categorical':
    case 'boolean':
    case 'date':
      return { options: liveOptions(rows, filter) }
    case 'numeric':
      return { bins: liveBins(rows, filter) }
    default:
      // A text filter lists only its most common values, as shortcuts. They
      // are context for the search box, not a facet, so they stay static.
      return staticCounts(filter)
  }
}

export function liveOptions(rows: Row[], filter: FilterDescriptor): LiveOption[] {
  const tally = new Map<string, number>()
  for (const row of rows) {
    // NaN and null both read `NR`/`NA`, the same keys as the static options.
    const value = cellKey(row, filter.key)
    tally.set(value, (tally.get(value) ?? 0) + 1)
  }
  return (filter.options ?? []).map((option) => ({
    value: option.value,
    count: tally.get(option.value) ?? 0,
    total: option.count
  }))
}

/**
 * Count `rows` into the static bins, so the x axis and the brush handles stay
 * where they are and only the heights change.
 */
export function liveBins(rows: Row[], filter: FilterDescriptor): BinData[] {
  const bins = filter.bins ?? []
  const edges = filter.binEdges
  if (!edges || bins.length === 0) return bins
  const counts = new Array<number>(bins.length).fill(0)
  for (const row of rows) {
    const raw = row[filter.key]
    if (raw === null || raw === undefined) continue
    const value = Number(raw)
    if (Number.isNaN(value)) continue
    const index = binIndex(edges, value)
    if (index >= 0) counts[index] += 1
  }
  return bins.map((bin, index) => [bin[0], counts[index] > 0 ? counts[index] : '', bin[2], bin[3]])
}

/**
 * The bin of a value, by the rule of d3's `bin` (used by `toBins`): the left edge
 * is in, the right edge is out, and the last bin also holds its right edge.
 * -1 when the value is outside the edges.
 */
function binIndex(edges: number[], value: number): number {
  const last = edges.length - 1
  if (value < edges[0] || value > edges[last]) return -1
  if (value === edges[last]) return last - 1
  let low = 0
  let high = last
  while (high - low > 1) {
    const middle = (low + high) >> 1
    if (value < edges[middle]) high = middle
    else low = middle
  }
  return low
}
