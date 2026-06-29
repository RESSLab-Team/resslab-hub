import type { SetOptionOpts } from 'echarts'

export const initOptions: InitOptions = {
  renderer: 'svg'
}
// Diff-merge each filter update instead of tearing down and re-instantiating the
// whole chart (notMerge:true was a full rebuild every tick). Merge animates the
// change as a cheap *update*; replaceMerge:['series'] drops series whose ids
// vanish on filtering (avoids the stale-series bug) while still animating the
// survivors. Chart series carry stable ids (SingleChart id=field,
// DoubleChart id=serie.name); SimpleParallelChart has a single series.
export const updateOptions: SetOptionOpts = {
  notMerge: false,
  replaceMerge: ['series']
}

/**
 * https://echarts.apache.org/en/api.html#echarts.init
 */
interface InitOptions {
  renderer: 'canvas' | 'svg'
}
