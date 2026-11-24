<script setup lang="ts">
/**
 * A "context" range filter: a slim overview of the whole distribution with two
 * draggable handles that define the active window — the focus+context idiom
 * from Observable/Tableau. The distribution is drawn with ECharts (bars/area);
 * the "[ ]" brackets and the veil over the active window are markLine/markArea.
 *
 * Dragging is handled by a transparent pointer overlay (not ECharts dataZoom),
 * which splits the *current window* into thirds: the left third grabs the left
 * handle, the right third the right handle, and the middle third moves the whole
 * window. This makes each target a large, predictable hit-area instead of the
 * fiddly fixed-pixel handles a dataZoom slider gives.
 *
 * The x-axis spans the *stable* full extent [min, max] (the data bounds, which
 * don't shrink when a filter is applied), so the handles always have room to be
 * dragged back out. The flanking number inputs keep precise values typeable.
 */
import { initOptions, stackBrushSeries } from '@/components/commons/charts/utils'
import { isBrushDragging } from '@/composables/interactionState'
import { echartsTheme } from '@/plugins/echarts-theme'
import { blendHex } from '@/utils/palette'
import type { EChartsOption } from 'echarts'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, MarkAreaComponent, MarkLineComponent } from 'echarts/components'
import { use } from 'echarts/core'
import { SVGRenderer } from 'echarts/renderers'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import VChart from 'vue-echarts'

use([SVGRenderer, LineChart, BarChart, GridComponent, MarkLineComponent, MarkAreaComponent])

/** One stacked band of the overview: its exact main-chart colour and its
 *  [value, count] points (raw counts, not cumulative). All bands share the same
 *  x positions; the brush stacks them itself, see stackBrushSeries. */
export interface BrushSeries {
  color: string
  data: [number, number][]
}

const props = withDefaults(
  defineProps<{
    modelValue?: [number, number]
    min: number
    max: number
    // The distribution as one or more stacked series, each carrying the exact
    // colour of the matching main-chart series (sorted by value, shared x).
    series?: BrushSeries[]
    step?: number
    type?: 'bar' | 'line'
    // Bin boundaries [e0…eN] for bar histograms. When given, the brush positions
    // bars in *bin-index* space — each bin an equal slot, exactly like the main
    // chart's category axis — so they line up pixel-for-pixel even though d3's
    // first/last bins are partial-width. Filter values stay in real units
    // (converted through the edges). Omit for line/date series, which use a plain
    // value axis.
    binEdges?: number[]
    // Render the handle/bound values through a formatter (used by the date variant).
    formatter?: (value: number) => string
    // Where the min/max fields sit: flanking the chart (chart strips, the rail),
    // or on their own line below it, under the handles they belong to (popovers,
    // where width is scarce and height is not).
    fields?: 'sides' | 'below'
  }>(),
  {
    modelValue: undefined,
    series: () => [],
    step: 1,
    type: 'bar',
    binEdges: undefined,
    formatter: undefined,
    fields: 'sides'
  }
)
const emit = defineEmits<{
  (e: 'update:modelValue', value: [number, number]): void
  // Fires once when a drag gesture ends (pointer up / cancel). The parent uses it
  // to commit the crossfilter drag reactively and settle the live overlay.
  (e: 'dragend'): void
}>()

// Track the chart's pixel width so the bracket feet can be drawn at a constant
// pixel length (data-unit lengths would grow with the chart and look heavy when
// it's wide). Reactive so the option recomputes on resize.
const chartEl = ref<HTMLElement>()
const chartWidth = ref(0)
let widthObserver: ResizeObserver | undefined
onMounted(() => {
  if (chartEl.value && 'ResizeObserver' in window) {
    widthObserver = new ResizeObserver(() => {
      chartWidth.value = chartEl.value?.clientWidth ?? 0
    })
    widthObserver.observe(chartEl.value)
  }
})
onUnmounted(() => {
  widthObserver?.disconnect()
  if (dragRaf) cancelAnimationFrame(dragRaf)
  // Unmounting mid-drag (e.g. a route change while the pointer is down) must
  // release the global drag flag, or every chart stays frozen forever.
  if (dragMode.value) isBrushDragging.value = false
})

const actualMin = computed<number>(() => props.min - (props.min % props.step))
const actualMax = computed<number>(() => Math.ceil(props.max / props.step) * props.step)

// Bar histograms position in *bin-index* space so they match the main chart's
// (equal-width) category axis; everything else uses a plain value axis. `hasBins`
// switches between the two. Coordinates handed to ECharts (axis min/max, bar x,
// markLine/markArea) are "axis coordinates": a bin index in [0, N] when binned,
// else the real value. Filter values (range, modelValue, fields) stay real.
const hasBins = computed<boolean>(() => (props.binEdges?.length ?? 0) >= 2)
const binCount = computed<number>(() => (props.binEdges?.length ?? 1) - 1)

// Real-value clamp bounds for the filter window.
const realLo = computed<number>(() => (hasBins.value ? props.binEdges![0] : actualMin.value))
const realHi = computed<number>(() =>
  hasBins.value ? props.binEdges![binCount.value] : actualMax.value
)

// Axis-coordinate extent the ECharts x-axis spans.
const axisLo = computed<number>(() => (hasBins.value ? 0 : realLo.value))
const axisHi = computed<number>(() => (hasBins.value ? binCount.value : realHi.value))
const axisSpan = computed<number>(() =>
  Math.max(axisHi.value - axisLo.value, hasBins.value ? 1 : props.step)
)

// real value ⇄ axis coordinate. Binned: piecewise-linear through the bin edges so
// each bin fills one equal slot (a value inside bin i lands at i + its fraction
// across that bin; a bin centre lands exactly at i + 0.5, matching the category
// axis). Unbinned: identity.
function toAxis(value: number): number {
  if (!hasBins.value) return value
  const edges = props.binEdges!
  const last = binCount.value
  if (value <= edges[0]) return 0
  if (value >= edges[last]) return last
  for (let i = 0; i < last; i++) {
    if (value <= edges[i + 1]) {
      const width = edges[i + 1] - edges[i]
      return width > 0 ? i + (value - edges[i]) / width : i
    }
  }
  return last
}
function toReal(axis: number): number {
  if (!hasBins.value) return axis
  const edges = props.binEdges!
  const last = binCount.value
  if (axis <= 0) return edges[0]
  if (axis >= last) return edges[last]
  const i = Math.floor(axis)
  return edges[i] + (axis - i) * (edges[i + 1] - edges[i])
}

// Local copy of the window so a drag clamps/orders *immediately* (the v-model
// round-trip through the parent is too slow to correct an out-of-bounds drag
// live). applyRange/commitRange keep it valid; the parent stays in sync via emit.
const localRange = ref<[number, number]>(props.modelValue ?? [realLo.value, realHi.value])
watch(
  () => props.modelValue,
  (value) => {
    // Ignore echoes of our own emits while dragging, and no-op when unchanged, so
    // the round-trip through the parent can't cause an extra mid-drag re-render.
    if (!value || dragMode.value) return
    if (value[0] === localRange.value[0] && value[1] === localRange.value[1]) return
    localRange.value = [value[0], value[1]]
  }
)
const range = computed<[number, number]>(() => localRange.value)

// Last value we emitted, so throttled drag emits and the final commit can dedup
// and avoid re-notifying the parent with a range it already holds.
let lastEmitted: [number, number] | null = null
function emitRange(value: [number, number]): void {
  if (lastEmitted && lastEmitted[0] === value[0] && lastEmitted[1] === value[1]) return
  lastEmitted = value
  emit('update:modelValue', value)
}

// Order defensively (handles can never cross into lo > hi), update locally and
// emit. Used by the number fields via commitRange; drags update locally (setLocal)
// and emit on a throttle. No-ops when the window is unchanged.
function applyRange(value: [number, number]): void {
  const next: [number, number] = value[0] <= value[1] ? [value[0], value[1]] : [value[1], value[0]]
  if (next[0] === localRange.value[0] && next[1] === localRange.value[1]) return
  localRange.value = next
  emitRange([next[0], next[1]])
}

function commitRange(value: [number, number]): void {
  // Clamp each end to the real data extent so the handles can reach the very ends
  // of the chart — "fully open" sits at the chart edges.
  const clamp = (v: number) => Math.min(Math.max(v, realLo.value), realHi.value)
  applyRange([clamp(value[0]), clamp(value[1])])
}

const option = computed<EChartsOption>(() => {
  const isLine = props.type === 'line'
  const [lo, hi] = range.value
  const inWindow = (x: number) => x >= lo && x <= hi
  // Neutral theme greys for the chrome (brackets + veil/fog) so they read as
  // structure, not data. Picked by theme since ECharts can't resolve CSS vars.
  const dark = typeof document !== 'undefined' && document.body.classList.contains('theme-dark')
  const bracketColor = dark ? '#a8a8ac' : '#707070' // --fg-muted
  const veilColor = dark ? 'rgba(245,245,245,0.06)' : 'rgba(33,33,33,0.05)' // faint --fg wash
  // Out-of-window context is muted: bars drop opacity per slice; area series can't
  // be split per-segment, so the excluded zones are fogged with a bg-coloured
  // markArea instead (both leave the in-window data at the exact chart colour).
  const fogColor = dark ? 'rgba(11,11,13,0.55)' : 'rgba(255,255,255,0.55)' // --bg-app wash
  // Bands are stacked by painting them over each other (see stackBrushSeries),
  // so every fill must be opaque or the lower bands show through. The muted
  // states are therefore pre-blended toward the page background instead of
  // being drawn at a lower opacity (same result over an opaque background).
  const bgHex = dark ? '#0B0B0D' : '#FFFFFF' // --bg-app
  const muted = (color: string) => blendHex(color, bgHex, 0.72) // was opacity 0.28
  const areaHex = (color: string) => blendHex(color, bgHex, 0.3) // was opacity 0.7

  // Stacked height per x = sum across series; the bracket geometry uses the peak.
  const totals = new Map<number, number>()
  for (const serie of props.series) {
    for (const [x, count] of serie.data) totals.set(x, (totals.get(x) ?? 0) + count)
  }
  const maxCount = totals.size ? Math.max(...totals.values(), 1) : 1

  // Each window edge is a plain "[" / "]": a full-height rule with short inward
  // feet top and bottom. Geometry is in y-axis (count) units, so the y-axis is
  // pinned to [0, maxCount] below.
  // Foot length: a constant 5px in data units (falls back to a small span
  // fraction before the width is measured), so feet stay slim on wide charts.
  const FOOT_PX = 5
  const foot =
    chartWidth.value > 0 ? (FOOT_PX / chartWidth.value) * axisSpan.value : axisSpan.value * 0.02
  const seg = (
    a: [number, number],
    b: [number, number]
  ): [{ coord: [number, number] }, { coord: [number, number] }] => [{ coord: a }, { coord: b }]
  const bracket = (x: number, dir: number) => [
    seg([x, 0], [x, maxCount]), // full-height rule
    seg([x, maxCount], [x + dir, maxCount]), // top foot
    seg([x, 0], [x + dir, 0]) // bottom foot
  ]
  // Chrome (brackets + the veil over the active window) is attached to the first
  // rendered series. A markArea paints before its own series' graphics, so this
  // keeps the veil behind every band, as before.
  const chrome = {
    markLine: {
      silent: true,
      symbol: 'none',
      label: { show: false },
      lineStyle: { color: bracketColor, width: 1.5, type: 'solid' },
      data: [...bracket(toAxis(lo), foot), ...bracket(toAxis(hi), -foot)]
    },
    markArea: {
      silent: true,
      data: [[{ xAxis: toAxis(lo), itemStyle: { color: veilColor } }, { xAxis: toAxis(hi) }]]
    }
  }
  // Bars mute out-of-window slices one by one, but an area series is a single
  // shape, so line charts fog the excluded zones instead. The areas are opaque
  // now, so the fog has to paint *above* them: it rides on its own empty series
  // appended after every band.
  const fogSeries = isLine
    ? [
        {
          type: props.type,
          xAxisIndex: 0,
          silent: true,
          data: [] as [number, number][],
          markArea: {
            silent: true,
            data: [
              [{ xAxis: axisLo.value, itemStyle: { color: fogColor } }, { xAxis: toAxis(lo) }],
              [{ xAxis: toAxis(hi), itemStyle: { color: fogColor } }, { xAxis: axisHi.value }]
            ]
          }
        }
      ]
    : []

  // Cumulative tops, top band first: each band is drawn full height from the
  // baseline and the one below paints over its lower part. ECharts' `stack` is
  // useless here (it stacks x on a value axis), so this is the stack.
  const visibleSeries = stackBrushSeries(props.series).map((serie, index) => ({
    type: props.type,
    xAxisIndex: 0,
    smooth: false,
    symbol: isLine ? 'none' : undefined,
    silent: true,
    ...(index === 0 ? chrome : {}),
    ...(isLine
      ? {
          lineStyle: { width: 0 },
          // Opaque, pre-blended: the same look as the main chart's 0.7 areaStyle
          // opacity, but bands can't show through each other. Out-of-window
          // zones are fogged by fogSeries rather than recoloured.
          areaStyle: { color: areaHex(serie.color), opacity: 1 },
          data: serie.data
        }
      : {
          // 80% of the band matches the main chart's default barCategoryGap, so
          // brush bars are the same width as the chart's, not just same position.
          barWidth: '80%',
          // Every band sits in the same slot. Without this ECharts groups the
          // series side by side, one sub-slot each (`stack` used to hold them
          // together, and we no longer set it).
          barGap: '-100%',
          // Exact main-chart colour; out-of-window slices recede to a muted one.
          // x is mapped to axis (bin-index) space so bars sit in equal slots.
          data: serie.data.map(([value, count]) => ({
            value: [toAxis(value), count],
            itemStyle: { color: inWindow(value) ? serie.color : muted(serie.color) }
          }))
        })
  }))

  return {
    animation: false,
    // Plot fills its container edge-to-edge; the bracket rules (drawn across the
    // full y-range) then span the same band as the veil so the two read as one
    // height. The flanking number fields are what align this plot's width with
    // the main chart, whose grid is pinned to a matching inset.
    grid: { left: 0, right: 0, top: 1, bottom: 1 },
    xAxis: {
      // Series renders here; range is fixed to the visual extent so it never zooms.
      type: 'value',
      min: axisLo.value,
      max: axisHi.value,
      show: false
      // No boundaryGap: it's invalid (boolean) on a value axis and moot here
      // anyway since min/max pin the range explicitly.
    },
    yAxis: { type: 'value', show: false, min: 0, max: maxCount },
    series: [...visibleSeries, ...fogSeries] as EChartsOption['series']
  }
})

// ── Drag: a pointer overlay that splits the current window into thirds ────────
// Left third → drag the left handle, right third → drag the right handle, middle
// third → move the whole window. Each target scales with the window, so they
// stay easy to hit at any width (the old fixed-pixel handles did not).
const dragMode = ref<null | 'lo' | 'hi' | 'move'>(null)
const hoverCursor = ref('grab')
let dragStartX = 0
let dragStartRange: [number, number] = [0, 0]
// The plot rect captured at drag start (it can't change mid-drag) and a single
// queued rAF, so a burst of pointermove samples collapses to one update per frame.
let dragRect: DOMRect | null = null
let dragRaf = 0
let pendingX = 0
// Whether this gesture pushed any live value to the parent (used on pointer-up to
// decide whether a final commit is needed). No time-throttle any more: the parent
// update is a cheap imperative repaint (crossfilter bus), so we publish every frame.
let didLiveEmit = false

// Set the window locally *without* emitting — the brackets track the pointer
// cheaply while the parent emit is throttled separately (see scheduleDrag). Orders
// defensively so the handles can never cross into lo > hi; no-ops when unchanged so
// pointer moves within the same snapped bin don't re-render the brush.
function setLocal(value: [number, number]): void {
  const next: [number, number] = value[0] <= value[1] ? [value[0], value[1]] : [value[1], value[0]]
  if (next[0] === localRange.value[0] && next[1] === localRange.value[1]) return
  localRange.value = next
}

// Fractional steps (0.001 for a ratio column) would otherwise surface float
// noise like 0.30000000000000004 in the chip and the URL: round to the step's
// own decimals.
const stepDecimals = computed<number>(() => Math.max(0, -Math.floor(Math.log10(props.step))))
function snap(v: number): number {
  return Number((Math.round(v / props.step) * props.step).toFixed(stepDecimals.value))
}
// Pointer x → real value (through axis space, so binned charts invert the bin
// mapping back to a real value).
function valueAt(clientX: number, rect: DOMRect): number {
  const ratio = rect.width > 0 ? (clientX - rect.left) / rect.width : 0
  return toReal(axisLo.value + ratio * axisSpan.value)
}
// Which third of the current window a client-x falls in. Anything left of the
// window counts as the left handle, anything right of it as the right handle, so
// the whole plot is covered.
function zoneAt(clientX: number, rect: DOMRect): 'lo' | 'hi' | 'move' {
  const [lo, hi] = range.value
  const toPx = (v: number) => rect.left + ((toAxis(v) - axisLo.value) / axisSpan.value) * rect.width
  const loPx = toPx(lo)
  const hiPx = toPx(hi)
  const third = (hiPx - loPx) / 3
  if (clientX <= loPx + third) return 'lo'
  if (clientX >= hiPx - third) return 'hi'
  return 'move'
}

// Apply the active gesture for a pointer position (local-only; committed on
// pointer-up). Edge gestures move that handle to the pointer (clamped so it can't
// cross the other); the move gesture shifts the window as a unit, keeping width.
function updateDrag(clientX: number, rect: DOMRect): void {
  const [startLo, startHi] = dragStartRange
  if (dragMode.value === 'lo') {
    setLocal([Math.min(Math.max(snap(valueAt(clientX, rect)), realLo.value), startHi), startHi])
  } else if (dragMode.value === 'hi') {
    setLocal([startLo, Math.max(Math.min(snap(valueAt(clientX, rect)), realHi.value), startLo)])
  } else {
    // Move in axis space so the window keeps its pixel width regardless of the
    // (possibly non-uniform) bin widths, then convert the ends back to real.
    const aWidth = toAxis(startHi) - toAxis(startLo)
    let a = toAxis(startLo) + ((clientX - dragStartX) / rect.width) * axisSpan.value
    let b = a + aWidth
    if (a < axisLo.value) {
      a = axisLo.value
      b = a + aWidth
    }
    if (b > axisHi.value) {
      b = axisHi.value
      a = b - aWidth
    }
    setLocal([snap(toReal(a)), snap(toReal(b))])
  }
}

// Coalesce pointermove samples to at most one brush re-render per frame, and emit
// to the parent on a slower time throttle so the main chart follows without a
// re-render + refilter on every frame.
function scheduleDrag(clientX: number): void {
  pendingX = clientX
  if (dragRaf || !dragRect) return
  dragRaf = requestAnimationFrame(() => {
    dragRaf = 0
    if (!dragRect) return
    updateDrag(pendingX, dragRect)
    // Publish every frame — emitRange dedups when the snapped window is unchanged,
    // so holding the pointer still costs nothing.
    didLiveEmit = true
    emitRange([localRange.value[0], localRange.value[1]])
  })
}

function onPointerDown(event: PointerEvent): void {
  const el = event.currentTarget as HTMLElement
  dragRect = el.getBoundingClientRect()
  dragMode.value = zoneAt(event.clientX, dragRect)
  if (dragMode.value) isBrushDragging.value = true
  dragStartX = event.clientX
  dragStartRange = [...range.value] as [number, number]
  didLiveEmit = false
  el.setPointerCapture(event.pointerId)
  event.preventDefault()
  // A single click acts immediately: the chosen handle jumps to the click point
  // (a drag isn't required). For 'move' this is a zero-delta no-op, so clicking
  // in the middle never teleports the whole window.
  updateDrag(event.clientX, dragRect)
}

function onPointerMove(event: PointerEvent): void {
  if (!dragMode.value) {
    const rect = (event.currentTarget as HTMLElement).getBoundingClientRect()
    hoverCursor.value = zoneAt(event.clientX, rect) === 'move' ? 'grab' : 'ew-resize'
    return
  }
  scheduleDrag(event.clientX)
}

function onPointerUp(event: PointerEvent): void {
  if (!dragMode.value) return
  if (dragRaf) {
    cancelAnimationFrame(dragRaf)
    dragRaf = 0
  }
  dragMode.value = null
  dragRect = null
  isBrushDragging.value = false
  ;(event.currentTarget as HTMLElement).releasePointerCapture?.(event.pointerId)
  // Commit the final window (emitRange dedups a value already pushed mid-drag).
  // Emit when it changed from the drag start, or to correct the parent if we
  // pushed intermediate values but ended back where we began. A plain click in the
  // middle zone (no change, no live emit) stays silent.
  const cur: [number, number] = [localRange.value[0], localRange.value[1]]
  if (cur[0] !== dragStartRange[0] || cur[1] !== dragStartRange[1] || didLiveEmit) emitRange(cur)
  // Always signal drag end (even for a no-op click), so a crossfilter parent can
  // commit + unfreeze and the charts never get stuck in the frozen live state.
  emit('dragend')
}

const overlayCursor = computed(() =>
  dragMode.value === 'move' ? 'grabbing' : dragMode.value ? 'ew-resize' : hoverCursor.value
)

const fieldClass = 'mt-0 pt-0'
function onMinChanged(event: Event): void {
  commitRange([Number((event.target as HTMLInputElement).value), range.value[1]])
}
function onMaxChanged(event: Event): void {
  commitRange([range.value[0], Number((event.target as HTMLInputElement).value)])
}
const displayMin = computed(() =>
  props.formatter ? props.formatter(range.value[0]) : range.value[0]
)
const displayMax = computed(() =>
  props.formatter ? props.formatter(range.value[1]) : range.value[1]
)
</script>

<template>
  <div class="dist-brush" :class="{ 'dist-brush--stacked': fields === 'below' }">
    <!-- DOM order is always min, chart, max; the stacked layout reorders with
         flex `order` so the chart takes the first line and the fields the second. -->
    <v-text-field
      v-if="!formatter"
      :class="[fieldClass, 'dist-brush__min']"
      density="compact"
      hide-details
      :max="actualMax"
      :min="actualMin"
      :model-value="range[0]"
      single-line
      type="number"
      variant="underlined"
      @change="onMinChanged"
    />
    <span v-else class="dist-brush__bound dist-brush__min">{{ displayMin }}</span>
    <div ref="chartEl" class="dist-brush__chart">
      <v-chart
        class="dist-brush__canvas"
        :theme="echartsTheme"
        :init-options="initOptions"
        :option="option"
        :update-options="{ notMerge: false }"
        autoresize
      />
      <!-- Transparent drag surface: thirds-based handle/move hit-testing. -->
      <div
        class="dist-brush__overlay"
        :style="{ cursor: overlayCursor }"
        @pointercancel="onPointerUp"
        @pointerdown="onPointerDown"
        @pointermove="onPointerMove"
        @pointerup="onPointerUp"
      />
    </div>
    <v-text-field
      v-if="!formatter"
      :class="[fieldClass, 'dist-brush__max']"
      density="compact"
      hide-details
      :max="actualMax"
      :min="actualMin"
      :model-value="range[1]"
      single-line
      type="number"
      variant="underlined"
      @change="onMaxChanged"
    />
    <span v-else class="dist-brush__bound dist-brush__max">{{ displayMax }}</span>
  </div>
</template>

<style scoped>
.dist-brush {
  display: flex;
  align-items: stretch;
  gap: 10px;
}
/* Fields below the chart: the chart wraps onto its own full-width line first,
   the bounds share the line under it, each under the handle it controls. */
.dist-brush--stacked {
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 4px 10px;
}
.dist-brush--stacked .dist-brush__chart {
  order: -1;
  flex: 1 1 100%;
}
.dist-brush--stacked :deep(.v-text-field),
.dist-brush--stacked .dist-brush__bound {
  flex: 0 0 auto;
  width: 72px;
  align-self: auto;
}
.dist-brush--stacked :deep(.dist-brush__min .v-field__input),
.dist-brush--stacked :deep(.dist-brush__min .v-field__input input),
.dist-brush--stacked .dist-brush__bound.dist-brush__min {
  text-align: left;
}
.dist-brush--stacked :deep(.dist-brush__max .v-field__input),
.dist-brush--stacked :deep(.dist-brush__max .v-field__input input),
.dist-brush--stacked .dist-brush__bound.dist-brush__max {
  text-align: right;
}
.dist-brush__chart {
  position: relative;
  flex: 1 1 auto;
  min-width: 0;
  height: 44px;
  /* Structural baseline the bars sit on — a single Swiss hairline rule. */
  border-bottom: 1px solid var(--border, #d5d5d5);
}
.dist-brush__canvas {
  width: 100%;
  height: 100%;
}
/* Drag surface over the plot: spans exactly the grid (left:0/right:0), so client
   coordinates map linearly to the axis extent. touch-action:none keeps a drag
   from scrolling the page on touch devices. */
.dist-brush__overlay {
  position: absolute;
  inset: 0;
  touch-action: none;
}
/* Compact numeric fields. Width is mirrored by DoubleChart's brushFlank (40 + the
   10px gap) to keep the brush plot aligned with the main chart. Bottom-aligned so
   the field's underline sits on the chart's baseline rule. */
.dist-brush :deep(.v-text-field) {
  flex: 0 0 40px;
  width: 40px;
  align-self: flex-end;
  margin-bottom: 0;
}
/* Strip the Vuetify chrome down to a flat, tabular, hairline-ruled field, with
   the value sitting just above the underline (close to the chart baseline). */
.dist-brush :deep(.v-field__field) {
  align-items: flex-end;
}
.dist-brush :deep(.v-field__input) {
  padding: 0 0 1px;
  min-height: 0;
  font-size: var(--fs-sm, 0.875rem);
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.01em;
  text-align: center;
  color: var(--fg, #212121);
}
.dist-brush :deep(.v-field__input input) {
  text-align: center;
}
/* Hide the number spinners — Swiss fields stay clean. */
.dist-brush :deep(input[type='number']::-webkit-inner-spin-button),
.dist-brush :deep(input[type='number']::-webkit-outer-spin-button) {
  appearance: none;
  margin: 0;
}
.dist-brush :deep(input[type='number']) {
  -moz-appearance: textfield;
}
/* Date bounds need room for an ISO date; width is mirrored by DoubleChart's
   brushFlank (84 + the 10px gap). */
.dist-brush__bound {
  flex: 0 0 84px;
  width: 84px;
  align-self: flex-end;
  padding-bottom: 2px;
  font-size: var(--fs-sm, 0.875rem);
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.01em;
  color: var(--fg-muted, #707070);
  text-align: center;
  white-space: nowrap;
}
</style>
