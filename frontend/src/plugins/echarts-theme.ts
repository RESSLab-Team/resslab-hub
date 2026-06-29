/* ============================================================
   RESSLab Hub — brutalist ECharts theme (EPFL design handoff)
   Applied globally via vue-echarts THEME_KEY (see main.ts), so every
   <v-chart> picks it up without per-component wiring.

   Design language (from the handoff's charts-lib.js):
     · hairline axes  (#C1C1C1)
     · very light, solid gridlines  (#ECECEC)
     · mono tick labels  (#8E8E8E)
     · square markers  (symbol: 'rect') — circles are never used
     · square bar corners
     · restrained red reserved for selection/emphasis, not series fills

   NOTE: ECharts measures/renders text from a literal font string — CSS
   custom properties (var(--font-mono)) do NOT resolve here, so the Suisse/
   mono stacks are inlined to mirror epfl-tokens.css.
   ============================================================ */

const SANS = "'Suisse Int\\'l', 'SuisseIntl', Arial, 'Helvetica Neue', Helvetica, sans-serif"
const MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Monaco, Consolas, monospace"

const AXIS = '#c1c1c1' // hairline axis line
const GRID = '#ececec' // very light gridline
const TICK = '#8e8e8e' // mono tick label
const NAME = '#6e6e73' // muted axis-name ink (uniform across every chart)
const INK = '#212121' // soft black

// Categorical series palette — Okabe–Ito (colorblind-safe), handoff order.
// EPFL red stays reserved for selection/emphasis and is never a series color.
const SERIES = [
  '#0072b2', // blue
  '#e69f00', // amber
  '#009e73', // green
  '#cc79a7', // reddish purple
  '#56b4e9', // sky
  '#d55e00', // vermillion
  '#5b6b78', // slate
  '#332288' // indigo
]

const axisCommon = {
  axisLine: { lineStyle: { color: AXIS, width: 1 } },
  axisTick: { lineStyle: { color: AXIS, width: 1 } },
  axisLabel: { color: TICK, fontFamily: MONO, fontSize: 11 },
  splitLine: { lineStyle: { color: GRID, width: 1, type: 'solid' } },
  // Axis names (titles): one treatment everywhere — muted grey, mono, regular
  // weight (never black/bold), matching the mono tick labels above.
  nameTextStyle: { color: NAME, fontFamily: MONO, fontWeight: 'normal' as const, fontSize: 11 }
}

export const echartsTheme = {
  color: SERIES,
  backgroundColor: 'transparent',
  textStyle: { fontFamily: SANS },

  // Snappy filter updates: a short, linear transition instead of ECharts' default
  // ~1s elasticOut ENTER animation, which (under setOption notMerge) replayed in
  // full on every chart on every filter tick — the main source of perceived lag.
  // Set in the theme so it applies to every <v-chart> and survives notMerge
  // (which discards only the user option, not the theme).
  animation: true,
  animationDuration: 300,
  animationDurationUpdate: 300,
  animationEasing: 'cubicOut' as const,
  animationEasingUpdate: 'cubicOut' as const,
  animationThreshold: 1000, // skip animation entirely past 1000 elements (parallel safety net)

  title: {
    textStyle: { color: INK, fontFamily: SANS, fontWeight: 'normal' as const }
  },

  // Category axis: keep the baseline, drop the perpendicular gridlines.
  categoryAxis: {
    ...axisCommon,
    splitLine: { show: false }
  },
  valueAxis: {
    ...axisCommon,
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: { show: true, lineStyle: { color: GRID, width: 1, type: 'solid' } }
  },
  logAxis: { ...axisCommon, axisLine: { show: false }, axisTick: { show: false } },
  timeAxis: { ...axisCommon },

  // Square markers everywhere; hairline-friendly line weight.
  line: { symbol: 'rect', symbolSize: 7, lineStyle: { width: 2 } },
  scatter: { symbol: 'rect', symbolSize: 8 },
  // Square bar corners (no lift, no rounding).
  bar: { itemStyle: { borderRadius: 0 } },

  legend: {
    textStyle: { color: INK, fontFamily: SANS, fontSize: 12 },
    // Small square swatches (handoff) — default ECharts markers are wide rects.
    icon: 'rect',
    itemWidth: 10,
    itemHeight: 10
  }
}

export default echartsTheme
