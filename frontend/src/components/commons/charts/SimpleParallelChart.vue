<script setup lang="ts">
import { isDivision, type ParallelField, type ParallelSelection } from '@/composables/chart'
import { useEChart } from '@/composables/useEChart'
import i18n from '@/plugins/i18n'
import { AXIS, INK_SLATE, NAME, RED, SANS, TICK } from '@/plugins/echarts-theme'
import type { Value } from '@/utils/common'
import type { ZRFontWeight } from '@/utils/echarts'
import type { EChartsOption } from 'echarts'
import { ParallelChart } from 'echarts/charts'
import { BrushComponent, ToolboxComponent } from 'echarts/components'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import type { CallbackDataParams } from 'echarts/types/dist/shared'
import { chain, merge, zip } from 'lodash'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, unref, watch } from 'vue'

// Canvas (not the app-wide SVG) for this one chart: it draws one polyline per
// filtered record, so element count scales with the result set — canvas keeps
// that cheap where SVG's DOM cost would not. devicePixelRatio keeps it crisp.
use([CanvasRenderer, ParallelChart, BrushComponent, ToolboxComponent])

// TODO add genericity https://github.com/vuejs/rfcs/discussions/436
type F = string
const props = withDefaults(
  defineProps<{
    data: (number | string)[][]
    fields?: ParallelField<F>[]
    ids: string[]
    labelPrefix?: string
    requestFields: F[]
    isFiltered: boolean
    // Zoom state lives in useParallelChart (it swaps the chart's data query);
    // the component only toggles it via update:zoomed.
    zoomed?: boolean
    // Ids selected by the committed id clause (line click / derived-axis
    // fallback), painted as the red overlay when no brush selection exists.
    highlightIds?: string[]
    // Local (in-browser) filtering is instant, so disable ECharts animation
    // entirely — the enter/update/exit transitions otherwise read as a load and
    // cost frames on every filter tick.
    animate?: boolean
  }>(),
  {
    data: () => [],
    fields: () => [],
    ids: () => [],
    labelPrefix: '',
    zoomed: false,
    highlightIds: () => [],
    animate: true,
    requestFields: () => []
  }
)
const emit = defineEmits<{
  (e: 'change:searches', value?: Value): void
  // Brushing filters interactively: live frames go to the crossfilter bus while
  // the pointer is down, and the selection is committed once on pointer-up. The
  // host wrapper wires these to useParallelChart's publishSelection/commitSelection.
  (e: 'brush:live', selection: ParallelSelection): void
  (e: 'brush:commit', selection: ParallelSelection): void
  (e: 'update:zoomed', zoomed: boolean): void
}>()

const selectedIds = ref<string[]>([])
// The brushed rows, re-fed to the red overlay series so the selection reads as
// red polylines instead of "slightly less faded grey".
const selectedRows = ref<(string | number)[][]>([])

const transposedData = computed<(string | number)[][]>(
  () => zip(...props.data) as (string | number)[][]
)

// Position of each request field, precomputed once — the data projection and
// getValues below run per row × field, so an O(1) lookup replaces repeated
// requestFields.indexOf(...) (was O(rows × fields × requestFields) per recompute).
const fieldIndex = computed<Map<F, number>>(
  () => new Map(props.requestFields.map((f, i) => [f, i]))
)

const chartHeight = computed(() => {
  // Find the field with the most categories
  const maxCategories = Math.max(
    ...props.fields.map((field) => {
      const values = getValues(field)?.filter((d) => d != null && d !== undefined)
      if (!values || typeof values[0] === 'number') return 0
      return new Set(values).size
    })
  )

  // Base height + additional height per category
  const baseHeight = 300
  const heightPerCategory = 30
  const additionalHeight = Math.max(0, maxCategories - 10) * heightPerCategory

  return baseHeight + additionalHeight
})

function axisIdOf(field: ParallelField<F>): string {
  return typeof field.id === 'string'
    ? field.id
    : isDivision(field.id)
    ? `${field.id.dividend}/${field.id.divisor}`
    : field.id.key
}

// Per-axis brush metadata: which query key a brushed interval translates to
// (the column itself, or an `a/b` derived-ratio key for division axes — the
// client query engine evaluates those), the axis position, and — for category
// axes — the ordered display values plus the display→raw reverse mapping
// needed to turn a brushed band back into raw column values.
interface AxisMeta {
  index: number
  filterKey?: string
  categories?: string[]
  reverse?: Map<string, string>
}
const axisMeta = computed<Map<string, AxisMeta>>(() => {
  const meta = new Map<string, AxisMeta>()
  props.fields.forEach((field, index) => {
    const id = axisIdOf(field)
    // Plain fields and divisions filter by clause; computed axes have no query
    // representation (arbitrary compute fn) and fall back to the id selection.
    const filterKey =
      typeof field.id === 'string' || isDivision(field.id) ? axisIdOf(field) : undefined
    const values = getValues(field)
    const type = values ? typeof values.find((v) => v != null) : 'number'
    if (type === 'number') {
      meta.set(id, { index, filterKey })
    } else {
      const categories = (field.sortValues || chain(values).uniq().sort().value()) as string[]
      const reverse = field.mapping
        ? new Map([...field.mapping].map(([raw, display]) => [display, raw]))
        : undefined
      meta.set(id, { index, filterKey, categories, reverse })
    }
  })
  return meta
})

// One axis treatment for every dimension, restated locally because the theme's
// valueAxis.axisLine.show: false outranks parallelAxisDefault — without a
// per-axis override the spines vanish. Values mirror echarts-theme.ts.
const axisStyle = {
  nameLocation: 'end' as const,
  nameGap: 16,
  nameTextStyle: {
    color: NAME,
    fontFamily: SANS,
    fontWeight: 'normal' as ZRFontWeight,
    fontSize: 11,
    lineHeight: 14
  },
  axisLine: { show: true, lineStyle: { color: AXIS, width: 1 } },
  axisTick: { show: true, length: 3, lineStyle: { color: AXIS, width: 1 } },
  axisLabel: { color: TICK, fontFamily: SANS, fontSize: 10 },
  splitLine: { show: false },
  // The brush band — red, like the overlay series it drives.
  areaSelectStyle: { width: 18, borderWidth: 1, borderColor: RED, color: RED, opacity: 0.12 }
}

// Row-major projection of props.data onto the configured fields — feeds the
// main series and, sliced by the brushed indices, the selection overlay.
const projectedRows = computed<(string | number)[][]>(() => {
  const idx = unref(fieldIndex)
  return props.data.map((d) =>
    props.fields.map((f) => {
      if (typeof f.id === 'string') {
        const value = d[idx.get(f.id) ?? -1]
        if (f.mapping && typeof value === 'string') return f.mapping.get(value) || value
        else return value
      } else if (isDivision(f.id)) {
        return (
          (d[idx.get(f.id.dividend) ?? -1] as number) / (d[idx.get(f.id.divisor) ?? -1] as number)
        )
      } else {
        const values = f.id.fields.map((field) => {
          const v = d[idx.get(field) ?? -1]
          return v == null ? null : (v as number)
        })
        return f.id.compute(values) as number
      }
    })
  )
})

// Red overlay rows: the live brush selection, or — when none — the committed
// id selection (a clicked line), matched exactly against the current ids.
// Skipped while zoomed: the whole view is the selection there.
const overlayRows = computed<(string | number)[][]>(() => {
  if (selectedRows.value.length) return selectedRows.value
  if (props.zoomed || !props.highlightIds.length) return []
  const targets = new Set(props.highlightIds)
  const rows: (string | number)[][] = []
  props.ids.forEach((id, i) => {
    if (targets.has(id)) rows.push(projectedRows.value[i])
  })
  return rows
})

const option = computed<EChartsOption>(() => ({
  animation: props.animate,
  parallel: {
    left: 66,
    top: 44,
    right: 48,
    bottom: 16,
    axisExpandable: true,
    // The brush band style must also live here: ECharts reads areaSelectStyle
    // from the coordinate system's axis defaults, not the per-axis option.
    parallelAxisDefault: { areaSelectStyle: axisStyle.areaSelectStyle }
  },
  parallelAxis: props.fields.map((field, index) => {
    const id = axisIdOf(field)
    const name = field.name ?? i18n.global.t(props.labelPrefix + id).toString()
    const meta = axisMeta.value.get(id)
    const base = merge({ id: id, dim: index, name: name }, axisStyle)
    if (meta?.categories) {
      return merge(base, {
        nameLocation: 'start' as const,
        inverse: true,
        type: 'category' as const,
        axisTick: { alignWithLabel: true },
        data: meta.categories
      })
    }
    return merge(base, { type: 'value' as const, scale: true })
  }),
  series: [
    {
      id: 'lines',
      type: 'parallel',
      // A parallel view has no categorical dimension driving colour, so hue
      // carries no information — grey ink + density, red stays for selection.
      lineStyle: { color: INK_SLATE, width: 1, opacity: 0.3 },
      inactiveOpacity: 0.04,
      activeOpacity: 0.3,
      emphasis: { focus: 'series', lineStyle: { color: RED, width: 1.8, opacity: 1 } },
      data: projectedRows.value
    },
    // ECharts can't recolour active lines within one parallel series — this
    // overlay carries the brushed (or committed-id) rows.
    {
      id: 'selection',
      type: 'parallel',
      silent: true,
      z: 10,
      lineStyle: { color: RED, width: 1.2, opacity: 0.75 },
      data: overlayRows.value
    }
  ]
}))

function getValues(field: ParallelField): (string | number)[] {
  const transposedDataValue = unref(transposedData)
  const idx = unref(fieldIndex)
  if (typeof field.id === 'string') {
    const values = transposedDataValue[idx.get(field.id) ?? -1]
    if (field.mapping && values)
      return values.map((d) =>
        typeof d == 'string' ? (field.mapping as Map<string, string>).get(d) || d : d
      )
    else return values
  } else if (isDivision(field.id)) {
    return zip(
      transposedDataValue[idx.get(field.id.dividend) ?? -1],
      transposedDataValue[idx.get(field.id.divisor) ?? -1]
    )
      .map((v) => v as [number, number])
      .map((v) => v[0] / v[1])
  } else {
    const computed = field.id
    const columns = computed.fields.map((f) => transposedDataValue[idx.get(f) ?? -1] ?? [])
    const rowCount = columns[0]?.length ?? 0
    const values: (number | null)[] = []
    for (let i = 0; i < rowCount; i++) {
      const rowValues = columns.map((col) => {
        const v = col[i]
        return v == null ? null : (v as number)
      })
      values.push(computed.compute(rowValues))
    }
    return values as (string | number)[]
  }
}

const chartEl = ref<HTMLElement>()
const { render, getInstance } = useEChart(chartEl, () => option.value, {
  click: onClick,
  axisareaselected: onBrush
})

// ECharts quirk: on every render the parallel axis rebuilds its brush covers
// from the active intervals WITHOUT the axis areaSelectStyle (see echarts
// ParallelAxisView.getCoverInfoList), so a re-render repaints the band in the
// BrushController default blue (#D2DBEE). Restyle the cover rects to the
// design's red after each paint.
function restyleBrushCovers(): void {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const zr = (getInstance() as any)?.getZr?.()
  if (!zr) return
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  for (const el of zr.storage.getDisplayList(true) as any[]) {
    if (el.name === 'main' && el.style?.fill === '#D2DBEE') {
      el.setStyle({ fill: RED, stroke: RED, lineWidth: 1, opacity: 0.12 })
    }
  }
}

// ── Brush gesture: live-filter while dragging, commit once on pointer-up ─────
// Same lifecycle as the distribution brushes (see crossfilterBus.ts): each brush
// change publishes a live frame so the other charts repaint mid-drag; releasing
// the pointer commits the clauses through Vue (table + URL, once) and settles.
let gestureActive = false
let brushChanged = false
let skippedRender = false
// Ignore brush events fired by our own restore/re-dispatch bookkeeping.
let suppressBrush = false
// Guard against re-entry while pushing a clamp-corrected interval back.
let reasserting = false

// Active brush bands, per axis id, in axis-value space (category-index space
// for category axes) — maintained from the axisareaselected event payloads.
const bands = new Map<string, number[][]>()
// Per-gesture classification (band moved vs edge-resized) and, for moves, the
// band width to preserve when ECharts clamps it against an axis end.
const gestureMode = new Map<string, 'move' | 'edge'>()
const moveWidth = new Map<string, number>()

const trimNumber = (value: number): string => String(Number(value.toPrecision(6)))

// Axis data extents, cached from the `rendered` hook. They can NOT be read
// during a brush event: the parallel coordinate system re-nices its scales
// after the event fires, so mid-event the scale still holds a stale [0, 1].
const axisExtents = new Map<string, [number, number]>()
function cacheAxisExtents(): void {
  // @ts-ignore private model access, like the brush read in onBrush
  const model = getInstance()?.getModel()
  if (!model) return
  axisMeta.value.forEach((meta, axisId) => {
    const extent: number[] | undefined = model
      .getComponent('parallelAxis', meta.index)
      ?.axis?.scale?.getExtent?.()
    if (extent && isFinite(extent[0]) && isFinite(extent[1])) {
      axisExtents.set(axisId, [Math.min(extent[0], extent[1]), Math.max(extent[0], extent[1])])
    }
  })
}

// While a band is dragged past an axis end, ECharts pins the leading edge and
// keeps moving the trailing one, shrinking the window. Classify the gesture
// from its first event (a move changes both edges, an edge-resize only one)
// and, for moves, keep the original width anchored at the axis end instead.
// Returns `incoming` (same reference) when no correction applies.
function clampMovedBand(axisId: string, incoming: number[]): number[] {
  const previous = bands.get(axisId)?.[0]
  const extent = axisExtents.get(axisId)
  if (!previous || !extent) return incoming
  const eps = (extent[1] - extent[0]) * 1e-6
  const lo = Math.min(...incoming)
  const hi = Math.max(...incoming)
  let mode = gestureMode.get(axisId)
  if (!mode) {
    const dLo = Math.abs(lo - Math.min(...previous))
    const dHi = Math.abs(hi - Math.max(...previous))
    if (dLo > eps && dHi > eps) {
      mode = 'move'
      moveWidth.set(axisId, Math.max(...previous) - Math.min(...previous))
    } else if (dLo > eps || dHi > eps) {
      mode = 'edge'
    }
    if (mode) gestureMode.set(axisId, mode)
  }
  if (mode !== 'move') return incoming
  const width = moveWidth.get(axisId) ?? hi - lo
  const anchoredLo = Math.min(Math.max(lo, extent[0]), Math.max(extent[0], extent[1] - width))
  const anchoredHi = Math.min(anchoredLo + width, extent[1])
  if (Math.abs(anchoredLo - lo) < eps && Math.abs(anchoredHi - hi) < eps) return incoming
  return [anchoredLo, anchoredHi]
}

// Translate the current bands into what to commit: one query clause per brushed
// axis (`min<<max` range for numeric and division axes, a value set for
// categories). Only a computed axis (arbitrary compute fn) or a multi-band axis
// has no clause representation — those fall back to the raw id selection.
function selectionPayload(): ParallelSelection {
  const clauses: Record<string, string> = {}
  for (const [axisId, intervals] of bands) {
    const meta = axisMeta.value.get(axisId)
    if (!meta?.filterKey || intervals.length !== 1) return { ids: selectedIds.value }
    const lo = Math.min(...intervals[0])
    const hi = Math.max(...intervals[0])
    if (meta.categories) {
      const from = Math.max(0, Math.ceil(lo))
      const to = Math.min(meta.categories.length - 1, Math.floor(hi))
      const values = meta.categories
        .slice(from, to + 1)
        .map((display) => meta.reverse?.get(display) ?? display)
      if (!values.length) return { ids: selectedIds.value }
      clauses[meta.filterKey] = values.join(',')
    } else {
      clauses[meta.filterKey] = `${trimNumber(lo)}<<${trimNumber(hi)}`
    }
  }
  return { clauses }
}

// Reactive renders are frozen during a gesture — a full setOption per brush
// frame is wasted work (only the overlay changes) and the overlay gets its own
// targeted merge in onBrush. A skipped frame is replayed on pointer-up.
watch(option, (value) => {
  if (gestureActive) {
    skippedRender = true
    return
  }
  render(value)
})

function onPointerDown(): void {
  gestureActive = true
  brushChanged = false
  gestureMode.clear()
  moveWidth.clear()
}

function onPointerUp(): void {
  if (!gestureActive) return
  gestureActive = false
  // Next task, so a brush event landing between ECharts' own mouseup handling
  // and this listener is still included in the commit.
  setTimeout(() => {
    if (brushChanged) {
      brushChanged = false
      // Re-assert the (possibly clamp-corrected) bands so a window that shrank
      // against an axis end snaps back to its full width, then repaint + commit.
      for (const [axisId, intervals] of bands) {
        getInstance()?.dispatchAction({ type: 'axisAreaSelect', parallelAxisId: axisId, intervals })
      }
      skippedRender = false
      render(option.value)
      emit('brush:commit', selectionPayload())
    } else if (skippedRender) {
      skippedRender = false
      render(option.value)
    }
  })
}

onMounted(() => {
  window.addEventListener('pointerup', onPointerUp)
  // After every ECharts paint: re-apply the red band (covers are rebuilt in
  // default blue on each render — see restyleBrushCovers; the fill guard makes
  // this idempotent so the restyle-triggered repaint doesn't loop) and refresh
  // the axis-extent cache (only valid post-render — see cacheAxisExtents).
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  ;(getInstance() as any)?.on('rendered', () => {
    restyleBrushCovers()
    cacheAxisExtents()
  })
})
onBeforeUnmount(() => window.removeEventListener('pointerup', onPointerUp))

function onClick(params: CallbackDataParams): void {
  emit('change:searches', props.ids[params.dataIndex])
}

function onBrush(params: CallbackDataParams): void {
  if (suppressBrush || reasserting) return
  const brush = params as unknown as { parallelAxisId?: string; intervals?: number[][] }
  if (brush.parallelAxisId) {
    let intervals = brush.intervals ?? []
    let corrected = false
    if (gestureActive && intervals.length === 1) {
      const clamped = clampMovedBand(brush.parallelAxisId, intervals[0])
      corrected = clamped !== intervals[0]
      intervals = [clamped]
    }
    if (intervals.length) bands.set(brush.parallelAxisId, intervals)
    else bands.delete(brush.parallelAxisId)
    // Push the corrected interval straight back so the visible cover stops at
    // the axis end at full width instead of shrinking; the overlay setOption
    // below triggers the render that repositions the cover mid-drag.
    if (corrected) {
      reasserting = true
      getInstance()?.dispatchAction({
        type: 'axisAreaSelect',
        parallelAxisId: brush.parallelAxisId,
        intervals
      })
      reasserting = false
    }
  }
  // @ts-ignore reading the brush result still requires a private API
  // see https://github.com/apache/echarts/blob/d08664fffe9e6cb4851519e50cf8c7c42f0427ae/src/chart/parallel/ParallelSeries.ts#L105
  // or https://echarts.apache.org/en/api.html#events.axisareaselected
  const model = getInstance()?.getModel()
  const selectedIndexes: number[] = model?.getSeries()[0].getRawIndicesByActiveState('active') ?? []
  selectedIds.value = selectedIndexes.map((index) => props.ids[index])
  selectedRows.value = selectedIndexes.map((index) => projectedRows.value[index])
  if (gestureActive) {
    brushChanged = true
    // Overlay-only repaint (plain merge by series id) — the full option render
    // is frozen for the duration of the gesture.
    getInstance()?.setOption({ series: [{ id: 'selection', data: selectedRows.value }] })
    emit('brush:live', selectionPayload())
  }
}

// One toggle: zoom in on what the committed query filters (the same rows as
// the table — useParallelChart swaps the data query), or back out to the full
// domain. Clearing the filters themselves is the chart head's "remove filter".
function onToggleZoom(): void {
  if (props.zoomed) {
    emit('update:zoomed', false)
    // Data grows back asynchronously; once it lands, replay the kept bands so
    // covers, fade and overlay pick up where they left off.
    const restoreBands = new Map(bands)
    if (restoreBands.size) {
      const stop = watch(
        () => props.ids,
        () => {
          stop()
          nextTick(() => {
            for (const [axisId, intervals] of restoreBands) {
              getInstance()?.dispatchAction({
                type: 'axisAreaSelect',
                parallelAxisId: axisId,
                intervals
              })
            }
            render(option.value)
          })
        }
      )
    }
  } else {
    emit('update:zoomed', true)
    // The axes rescale to the filtered rows — covers and overlay would be
    // stale noise there. `bands` is kept as the memory for un-zooming.
    clearCovers()
  }
}

// Wipe the visible brush covers and the red overlay (not the bands map).
// `restore` (Toolbox) resets to the initial option, so re-render the current one.
function clearCovers(): void {
  suppressBrush = true
  getInstance()?.dispatchAction({ type: 'restore' })
  suppressBrush = false
  selectedIds.value = []
  selectedRows.value = []
  render(option.value)
}

function clearLocal(): void {
  bands.clear()
  gestureMode.clear()
  moveWidth.clear()
  clearCovers()
  if (props.zoomed) emit('update:zoomed', false)
}

// External reset — the chart-cell's "remove filter" cleared this chart's
// clauses, so drop the now-stale zoom, bands and selection with it.
watch(
  () => props.isFiltered,
  (filtered) => {
    if (!filtered) clearLocal()
  }
)
</script>

<template>
  <div class="parallel-chart">
    <div
      class="parallel-chart__frame"
      :style="{ height: `${chartHeight}px` }"
      @pointerdown="onPointerDown"
    >
      <div ref="chartEl" class="parallel-chart__canvas" />
    </div>
    <div class="parallel-chart__actions">
      <span v-if="selectedIds.length > 0" class="parallel-chart__count">
        {{ $t('commons.parallel_selection_count', { n: selectedIds.length, total: ids.length }) }}
      </span>
      <span v-else-if="zoomed" class="parallel-chart__count">
        {{ $t('commons.parallel_zoomed_count', { total: ids.length }) }}
      </span>
      <button
        type="button"
        class="btn btn-sm"
        :class="zoomed ? 'btn-secondary' : 'btn-primary'"
        :disabled="!zoomed && selectedIds.length === 0 && !isFiltered"
        @click="onToggleZoom"
      >
        {{ zoomed ? $t('commons.unzoom') : $t('commons.zoom_selection') }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.parallel-chart {
  display: flex;
  flex-direction: column;
  padding-bottom: 8px;
}
.parallel-chart__frame {
  position: relative;
  width: 100%;
}
/* Absolute canvas so the ResizeObserver can't ratchet the frame height. */
.parallel-chart__canvas {
  position: absolute;
  inset: 0;
}
.parallel-chart__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 10px;
}
/* Micro count label, same eyebrow voice as the chart-head hint. */
.parallel-chart__count {
  margin-right: auto;
  font-family: var(--title-eyebrow-font);
  font-size: 0.625rem;
  font-weight: var(--title-eyebrow-weight);
  letter-spacing: var(--title-eyebrow-tracking);
  text-transform: uppercase;
  color: var(--fg-muted);
}
</style>
