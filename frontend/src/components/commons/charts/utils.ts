import type { SetOptionOpts } from 'echarts'

export const initOptions: InitOptions = {
  renderer: 'svg'
}
// Canvas for charts that re-render on every filter tick (dashboard SingleChart /
// DoubleChart): canvas repaints far cheaper than SVG's DOM diffing, and nothing
// exports these as SVG. Static views (UnitChart, model/fragility) keep crisp SVG.
export const canvasInitOptions: InitOptions = {
  renderer: 'canvas'
}
// NOTE: UnitChart does not use this — it derives its update options per render
// so it can skip `replaceMerge` while the series set is unchanged (see the
// comment there). Dashboard charts below keep the unconditional replace.
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

// Reused offscreen 2d context for measuring rendered text width. Used to lay the
// legend out inline, right after a variable-width (i18n) chart title, since
// ECharts has no flow layout between the title and the legend.
let measureCtx: CanvasRenderingContext2D | null | undefined
export function measureTextWidth(text: string, font: string): number {
  if (measureCtx === undefined) {
    measureCtx = document.createElement('canvas').getContext('2d')
  }
  if (!measureCtx) return text.length * 7 // fallback estimate if no 2d context
  measureCtx.font = font
  return measureCtx.measureText(text).width
}
