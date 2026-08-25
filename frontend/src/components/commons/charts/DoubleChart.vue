<script setup lang="ts">
import type { CountModel } from '@/backend'
import { measureTextWidth } from '@/components/commons/charts/utils'
import { useEChart, type LegendSelectChangedParams } from '@/composables/useEChart'
import DateDistributionBrush from '@/components/commons/sliders/DateDistributionBrush.vue'
import DistributionBrush, {
  type BrushSeries
} from '@/components/commons/sliders/DistributionBrush.vue'
import { invertMapping, type DoubleField, type DoubleFields } from '@/composables/chart'
import { SANS } from '@/plugins/echarts-theme'
import i18n from '@/plugins/i18n'
import { categoryColorScale, categoryDomain, type ColorScale } from '@/utils/categoryColors'
import { type Value } from '@/utils/common'
import { mapDateToNumber } from '@/utils/date'
import { toBins, type BinData } from '@/utils/statistics'
import type { EChartsOption } from 'echarts'
import { BarChart, LineChart } from 'echarts/charts'
import {
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent
} from 'echarts/components'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import type { CallbackDataParams } from 'echarts/types/dist/shared'
import { chain, clone, range } from 'lodash'
import { isBrushDragging } from '@/composables/interactionState'
import { publishLive, publishSettle, subscribeCrossfilter } from '@/composables/crossfilterBus'
import { dashboardQueryKey, withFieldClause } from '@/composables/dashboard'
import { computed, inject, onBeforeUnmount, onMounted, onUnmounted, ref, unref, watch } from 'vue'

use([
  CanvasRenderer,
  BarChart,
  LineChart,
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent
])

const props = withDefaults(
  defineProps<{
    // Stable value → color lookup for the second (stacked) field, shared by
    // every chart of the dashboard (see useDataset.colorFor). Omitted ⇒ a scale
    // derived from `allCounts`.
    colorFor?: ColorScale
    counts?: CountModel[]
    // Full unfiltered counts for the distribution brush — never changes shape.
    allCounts?: CountModel[]
    dateMin?: string
    dateMax?: string
    dateRange?: [string, string]
    fields: DoubleFields
    labelPrefix?: string
    numberMin?: number
    numberMax?: number
    numberRange?: [number, number]
    type?: 'bar' | 'line'
    // Local (in-browser) filtering is instant, so disable ECharts animation
    // entirely — the enter/update/exit transitions otherwise read as a load and
    // cost frames on every filter tick.
    animate?: boolean
    // Client-side (crossfilter) mode. When provided, a brush drag drives every
    // chart imperatively from the in-memory dataset via the crossfilter bus —
    // Vue's `query`/`searches` (and thus the table) stay put until pointer-up.
    // Omitted ⇒ server-side mode: the current reactive path (freeze via the
    // global drag flag, counts arrive over the network). See crossfilterBus.ts.
    liveCounts?: (query?: string) => CountModel[]
  }>(),
  {
    colorFor: undefined,
    allCounts: () => [],
    counts: () => [],
    dateMin: undefined,
    dateMax: undefined,
    dateRange: undefined,
    labelPrefix: '',
    numberMin: undefined,
    numberMax: undefined,
    numberRange: undefined,
    animate: true,
    type: 'bar',
    liveCounts: undefined
  }
)
const emit = defineEmits<{
  (e: 'change:searches', key: string, value?: Value): void
  (e: 'update:dateRange', value?: [string, string]): void
  (e: 'update:numberRange', value?: [number, number]): void
}>()

// Chart pixel width, tracked so the header (title + inline legend) can be
// centered as a group — ECharts has no flow layout that would centre a title
// and legend together, so we measure their widths and place them by hand.
const rootEl = ref<HTMLElement>()
const chartWidth = ref(0)
let resizeObserver: ResizeObserver | undefined
onMounted(() => {
  if (!rootEl.value) return
  resizeObserver = new ResizeObserver((entries) => {
    const width = Math.round(entries[0].contentRect.width)
    if (width !== chartWidth.value) chartWidth.value = width
  })
  resizeObserver.observe(rootEl.value)
})
onBeforeUnmount(() => resizeObserver?.disconnect())

// The committed dashboard query (provide/inject, not a prop — see dashboardQueryKey).
// Frozen for the duration of a drag: in crossfilter mode we don't commit to it
// until pointer-up, so the table and everything reactive stay put.
const query = inject(dashboardQueryKey, ref<string | undefined>(undefined))

// Freeze flag for the value axis. In crossfilter mode it's a plain (non-reactive)
// let driven by the bus, so flipping it never triggers a Vue re-render — the drag
// stays entirely off the scheduler. In server mode we fall back to the global drag
// flag (the reactive path still drives those charts). See isFrozen().
let frozen = false
const isFrozen = () => (props.liveCounts ? frozen : isBrushDragging.value)

const roundedMin = computed<number>(() => Math.floor(props.numberMin ?? 0))
const roundedMax = computed<number>(() => Math.ceil(props.numberMax ?? 0))

// Horizontal inset that lines the main plot up with the distribution brush below
// it. The brush's chart fills the gap between its flanking bound labels, so this
// must equal that flank width = bound width + the 10px flex gap. The two brush
// variants use different bound widths (DistributionBrush.vue): 40px for the
// editable numeric fields, 84px for the wider date labels.
const brushFlank = computed<number>(() => (props.dateMin && props.dateMax ? 94 : 50))

const actualNumberRange = computed({
  get: () => {
    if (props.numberRange !== undefined) return props.numberRange
    else if (props.numberMin !== undefined && props.numberMax !== undefined)
      // Fully-open = the brush's full extent (bin edges for histograms), so the
      // handles rest at the chart edges and this state reads as "no filter".
      return numberExtent.value
    else return undefined
  },
  set: (value) => {
    emit('update:numberRange', value)
  }
})
const actualDateRange = computed({
  get: () => {
    if (props.dateRange !== undefined) return props.dateRange
    else if (props.dateMin !== undefined && props.dateMax !== undefined)
      return [props.dateMin, props.dateMax] as [string, string]
    else return undefined
  },
  set: (value) => {
    if (value && value[0] === props.dateMin && value[1] === props.dateMax) {
      emit('update:dateRange', undefined)
    } else {
      emit('update:dateRange', value)
    }
  }
})
const defaultValue = computed(() => (props.type === 'line' ? 0 : ''))
const secondField = computed<string>(() => {
  const secondField: DoubleField = props.fields[1]
  if (typeof secondField === 'string') {
    return secondField
  } else {
    return secondField.id
  }
})
const mapSecondName = computed<(name: string) => string>(() => {
  const secondField: DoubleField = props.fields[1]
  if (typeof secondField === 'string') {
    return (name) => name
  } else {
    return (name) => secondField.mapping.get(name) ?? name
  }
})
// Display label → raw value, for the legend: ECharts hands back the series
// *name* (the mapped label, e.g. "Composite"), but the query wants the raw key
// ("True"), the same one the data-point click gets for free via `seriesId`.
const unmapSecondName = computed<(label: string) => string>(() => {
  const secondField: DoubleField = props.fields[1]
  if (typeof secondField === 'string') {
    return (label) => label
  } else {
    const inverse = invertMapping(secondField.mapping)
    return (label) => inverse.get(label) ?? label
  }
})
// While a brush is being dragged, derive the x categories/bins from the
// *unfiltered* distribution so the x axis stays static; the bar heights still
// come from the (live) filtered counts, so the bars shrink against a fixed axis.
// Reverts to the filtered set — and rescales — on release.
function deriveFirstKeys(countsData: CountModel[]): string[] {
  return chain(isFrozen() ? props.allCounts : countsData)
    .map((count) => count.names[0])
    .uniq()
    .sort()
    .value()
}
// Index counts by (first, second) once per recompute so each grid cell is an
// O(1) lookup — getCount was scanning all counts with a deep isEqual per cell
// (≈ O(firstKeys × secondKeys × counts)). The \u0001 separator cannot appear in
// a category name, so composite keys never collide.
function buildCountMap(countsData: CountModel[]): Map<string, number> {
  const map = new Map<string, number>()
  for (const count of countsData) {
    map.set(`${count.names[0]}\u0001${count.names[1]}`, count.value)
  }
  return map
}
const isHistogram = computed<boolean>(() => actualNumberRange.value !== undefined)
// Stacking/legend order of the second field: by total in the *unfiltered*
// dataset (ties alphabetical), so neither the order nor — through colorFor —
// the colors move when a filter reshuffles the filtered totals.
const secondDomain = computed<string[]>(() => categoryDomain(props.allCounts, 1))
const colorFor = computed<ColorScale>(
  () => props.colorFor ?? categoryColorScale(secondDomain.value)
)
// The brush overview replicates the main chart's stacked series — same category
// order, same colours, same counting — but built from the stable unfiltered
// allCounts so it never collapses as filters apply. When nothing is filtered,
// allCounts === counts, so the brush is pixel-for-pixel the chart's distribution.
const brushSecondKeys = secondDomain
const brushColors = computed<string[]>(() => brushSecondKeys.value.map(colorFor.value))
// Unique sorted x positions (numeric values / day numbers) across all series, so
// stacked area series line up on a shared axis.
function sortedUnique(values: number[]): number[] {
  return [...new Set(values.filter((v) => !isNaN(v)))].sort((a, b) => a - b)
}
function stackByKey(toX: (name: string) => number): BrushSeries[] {
  const keys = brushSecondKeys.value
  const colors = brushColors.value
  const xs = sortedUnique(props.allCounts.map((count) => toX(count.names[0])))
  return keys.map((key, index) => {
    const byX = new Map<number, number>()
    for (const count of props.allCounts) {
      if (count.names[1] !== key) continue
      const x = toX(count.names[0])
      if (isNaN(x)) continue
      byX.set(x, (byX.get(x) ?? 0) + count.value)
    }
    return { color: colors[index], data: xs.map((x) => [x, byX.get(x) ?? 0] as [number, number]) }
  })
}
// Bar histograms bin per series with the SAME d3/Sturges rule the main chart uses
// (toBins shares one set of bin edges across all category names), placing each bar
// at its bin centre and exposing the full bin-edge list. The brush positions bars
// in bin-index space from those edges, so they land exactly under the main chart's
// (equal-width) category bins despite d3's partial first/last bins. Line charts
// plot per value on a shared x axis.
const numberBins = computed<{
  series: BrushSeries[]
  min?: number
  max?: number
  edges?: number[]
}>(() => {
  if (props.type === 'line') return { series: stackByKey((name) => Number(name)) }
  const binData = props.allCounts
    .map((count) => ({ name: count.names[1], value: Number(count.names[0]), count: count.value }))
    .filter((d) => !isNaN(d.value))
  if (!binData.length) return { series: [] }
  const bins = toBins(brushSecondKeys.value, binData)
  const rows = bins[0].data
  // Boundaries [e0…eN] = the first bin's left edge then every bin's right edge.
  const edges = rows.length ? [rows[0][2], ...rows.map((d) => d[3])] : undefined
  return {
    series: bins.map((bin, index) => ({
      color: brushColors.value[index],
      data: bin.data.map(
        (d) => [(d[2] + d[3]) / 2, typeof d[1] === 'number' ? d[1] : 0] as [number, number]
      )
    })),
    min: edges?.[0],
    max: edges?.[edges.length - 1],
    edges
  }
})
const numberSeries = computed<BrushSeries[]>(() => numberBins.value.series)
const dateSeries = computed<BrushSeries[]>(() => stackByKey(mapDateToNumber))
// The brush's full extent: the bin-edge range for histograms (so handles reach
// the chart edges), else the rounded data extent. Used as the "fully open" /
// no-filter range too.
const numberExtent = computed<[number, number]>(() => {
  const { min, max } = numberBins.value
  return min !== undefined && max !== undefined ? [min, max] : [roundedMin.value, roundedMax.value]
})

// Ceiling for the pinned axis: the value the *unfiltered* distribution would
// reach, computed the same way each chart type stacks so it never clips. Any
// filtered subset is ≤ this, so pinning here is safe; ×1.05 mimics the headroom
// ECharts' auto axis leaves, so freezing from an unfiltered view barely moves.
const unfilteredYMax = computed<number | undefined>(() => {
  if (!props.allCounts.length) return undefined
  let rawMax: number
  if (props.type === 'line') {
    // Cumulative stacked line: the top-right point is the grand total.
    rawMax = props.allCounts.reduce((sum, count) => sum + count.value, 0)
  } else if (isHistogram.value) {
    // Binned stacked bars: sum the (unfiltered) brush series per bin.
    const series = props.dateMin && props.dateMax ? dateSeries.value : numberSeries.value
    const perBin = new Map<number, number>()
    for (const serie of series) {
      for (const [x, value] of serie.data) {
        perBin.set(x, (perBin.get(x) ?? 0) + (typeof value === 'number' ? value : 0))
      }
    }
    rawMax = perBin.size ? Math.max(...perBin.values()) : 0
  } else {
    // Plain category bars: sum the series stacked on each category.
    const perCategory = new Map<string, number>()
    for (const count of props.allCounts) {
      perCategory.set(count.names[0], (perCategory.get(count.names[0]) ?? 0) + count.value)
    }
    rawMax = perCategory.size ? Math.max(...perCategory.values()) : 0
  }
  return rawMax > 0 ? Math.ceil(rawMax * 1.05) : undefined
})
// Build the full ECharts option from a given counts array. Kept a plain function
// (not a closure over props.counts) so it serves two callers with the same code:
// the reactive `option` computed (normal filter changes) and the crossfilter bus
// (live drag frames, built imperatively from the in-memory dataset).
function buildOption(countsData: CountModel[]): EChartsOption {
  const firstKeysValue = deriveFirstKeys(countsData)
  const countMap = buildCountMap(countsData)
  // Keys present in the (filtered) data, in the stable unfiltered order; a key
  // missing from allCounts (still loading) falls back to its filtered rank.
  const domainIndex = new Map(secondDomain.value.map((key, index) => [key, index]))
  const secondKeys: string[] = chain(countsData)
    .groupBy((count) => count.names[1])
    .map((values, key) => ({
      key: key,
      value: values.reduce((total, count) => total + count.value, 0)
    }))
    .sortBy(
      (item) => domainIndex.get(item.key) ?? Number.MAX_SAFE_INTEGER,
      (item) => -item.value,
      (item) => item.key
    )
    .map((item) => item.key)
    .value()
  const colorForValue = colorFor.value
  const mapSecondNameValue = unref(mapSecondName)
  // Header row: the variable the colour encodes (e.g. "Number of doubler plates")
  // followed inline by the legend, centred as a group above the plot. Both use
  // the chart's own font (Suisse Int'l SANS, 12px, normal weight — matching the
  // ECharts theme) so measurements line up with what ECharts actually renders.
  const headerFont = `12px ${SANS}`
  const titleText = i18n.global.t(props.labelPrefix + secondField.value).toString()
  const titleWidth = measureTextWidth(titleText, headerFont)
  const titleGap = 12 // space between the title and the first legend item
  // Estimate the legend's rendered width so the whole group can be centred.
  // Per item ECharts lays out: marker (itemWidth) + ~5px marker-to-text gap +
  // label; consecutive items are separated by itemGap (10).
  const markerWidth = props.type === 'line' ? 18 : 10
  const legendWidth = secondKeys.reduce((width, key, index) => {
    const label = measureTextWidth(mapSecondNameValue(key), headerFont)
    return width + markerWidth + 5 + label + (index > 0 ? 10 : 0)
  }, 0)
  const groupWidth = titleWidth + titleGap + legendWidth
  // Left edge of the centred group; falls back to a small inset before the
  // container has been measured, or when the group is wider than the chart.
  const groupLeft = Math.max(8, Math.round((chartWidth.value - groupWidth) / 2))
  const option: EChartsOption = {
    animation: props.animate,
    title: {
      text: titleText,
      // fontWeight/family/colour come from the theme (normal weight); only the
      // compact 12px size is set here (theme title default is larger).
      textStyle: {
        fontSize: 12
      },
      left: groupLeft,
      // The title text is drawn dominant-baseline:central, so its top === its
      // vertical centre; ECharts centres legend content at legendTop + 7.5. These
      // two offsets are picked to put the title and the legend on one shared
      // vertical centre (≈12.5px) — otherwise the name rides above the swatches.
      top: 12,
      padding: 0
    },
    legend: {
      type: 'scroll',
      // Legend sits inline, right after the title, as a centred header row above
      // the plot (was below it). Its left edge is the title's right edge plus a
      // gap, computed here since ECharts has no flow layout between the two. Line
      // series read better with a thin line swatch; bars keep the square swatch.
      top: 5, // paired with title top:12 so both share a ~12.5px vertical centre
      left: groupLeft + titleWidth + titleGap,
      icon: 'rect',
      itemWidth: markerWidth,
      itemHeight: props.type === 'line' ? 2 : 10
    },
    grid: {
      // Header row (title + inline legend) lives at the top; the bottom must still
      // clear the x-axis name (nameGap 28 + its label) so it stays inside the
      // canvas and doesn't ride into the distribution brush rendered below.
      top: 44,
      bottom: 48,
      // Pin the horizontal insets to the distribution brush's flank so the main
      // plot and the brush overview below it line up exactly (see brushFlank).
      left: brushFlank.value,
      right: brushFlank.value
    },
    xAxis: {
      type: 'category',
      name: i18n.global.t(props.labelPrefix + props.fields[0]).toString(),
      nameLocation: 'middle',
      nameGap: 28,
      boundaryGap: props.type === 'bar',
      axisTick: {
        alignWithLabel: true
      }
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      // Freeze the scale while a brush is being dragged so the bars move against a
      // fixed axis; undefined lets ECharts auto-fit again on release.
      max: isFrozen() ? unfilteredYMax.value : undefined
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: props.type === 'bar' ? 'shadow' : undefined
      },
      confine: true
    },
    series: getSerie(secondKeys, firstKeysValue, countMap).map((serie) => ({
      id: serie.name,
      name: mapSecondNameValue(serie.name),
      type: props.type,
      // Per-series color (not the positional `option.color` list) so a category
      // keeps its hue whatever its rank in the current selection.
      color: colorForValue(serie.name),
      showSymbol: serie.data.length === 1, // show symbol to avoid empty chart
      stack: secondField.value,
      areaStyle: {},
      emphasis: {
        focus: 'series'
      },
      data: serie.data
    }))
  }
  return option
}
// Reactive option for the normal (non-drag) path: tile clicks, rail filters, and
// the pointer-up commit all flow through here.
const option = computed<EChartsOption>(() => buildOption(props.counts))

// Imperative renderer. The option is NOT bound as a reactive <v-chart :option>;
// instead we push updates via `render`, so a filter tick repaints the canvas
// without re-rendering this component's vnodes.
const chartEl = ref<HTMLElement>()
const { render, getInstance } = useEChart(chartEl, () => option.value, {
  click,
  legendselectchanged: legendSelectChanged
})

// Reactive renders (commit / tile click / rail), skipped while a drag is frozen —
// during a drag the bus is authoritative, so we mustn't let a stale reactive frame
// (old counts, unfrozen axis) overwrite the live one. A skipped frame is replayed
// on settle (see onSettle) so a mid-drag commit is never lost.
let skippedWhileFrozen = false
watch(option, (value) => {
  if (frozen) {
    skippedWhileFrozen = true
    return
  }
  render(value)
})

// ── Crossfilter: drive every chart imperatively during a drag ────────────────
// Only the dragged chart's brush changes its range, so only it publishes; every
// chart (this one included) subscribes and repaints from the in-memory dataset.
let lastLiveCounts: CountModel[] | null = null
const unsubscribe = subscribeCrossfilter({
  onLive: (liveQuery) => {
    if (!props.liveCounts) return // server mode: reactive path handles the drag
    frozen = true
    lastLiveCounts = props.liveCounts(liveQuery)
    render(buildOption(lastLiveCounts))
  },
  onSettle: () => {
    if (!props.liveCounts) return
    frozen = false
    // Repaint the last drag frame with the axis unfrozen; the reactive commit then
    // reconciles to the exact committed counts (usually an identical frame). If a
    // reactive update landed mid-drag and was skipped, replay the committed option
    // instead — it is the newer truth.
    render(skippedWhileFrozen ? option.value : buildOption(lastLiveCounts ?? props.counts))
    skippedWhileFrozen = false
    lastLiveCounts = null
  }
})
onUnmounted(unsubscribe)

// The live frame for the dragged range: the committed query with this field's
// clause swapped for the drag position (see withFieldClause in dashboard.ts).
function liveFrame(field: string, value?: string): string | undefined {
  return withFieldClause(query.value, field, value)
}

function numberSearchValue(value?: [number, number]): string | undefined {
  if (!value || isNaN(value[0]) || isNaN(value[1])) return undefined
  // A window covering the full extent (bin edges) means "no filter".
  if (props.numberMin !== undefined && props.numberMax !== undefined) {
    const [min, max] = numberExtent.value
    if (value[0] === min && value[1] === max) return undefined
  }
  return `${value[0]}<<${value[1]}`
}
function dateSearchValue(value?: [string, string]): string | undefined {
  if (!value) return undefined
  if (props.dateMin !== undefined && props.dateMax !== undefined) {
    if (value[0] === props.dateMin && value[1] === props.dateMax) return undefined
  }
  return `${value[0]}<<${value[1]}`
}

// During a crossfilter drag, publish the live query to the bus (no commit → the
// table stays put). Otherwise (server mode, number-field edits) commit reactively.
watch(actualNumberRange, (value) => {
  const searchValue = numberSearchValue(value)
  if (isBrushDragging.value && props.liveCounts) {
    publishLive(liveFrame(props.fields[0], searchValue))
  } else {
    emit('change:searches', props.fields[0], searchValue)
  }
})
watch(actualDateRange, (value) => {
  const searchValue = dateSearchValue(value)
  if (isBrushDragging.value && props.liveCounts) {
    publishLive(liveFrame(props.fields[0], searchValue))
  } else {
    emit('change:searches', props.fields[0], searchValue)
  }
})

// Pointer-up: commit the final range through Vue (updating the table and the rest,
// once) and settle the bus so every chart unfreezes. Fires regardless of whether
// the final value changed, so charts can never get stuck frozen.
function onNumberDragEnd(): void {
  emit('change:searches', props.fields[0], numberSearchValue(actualNumberRange.value))
  publishSettle()
}
function onDateDragEnd(): void {
  emit('change:searches', props.fields[0], dateSearchValue(actualDateRange.value))
  publishSettle()
}

function getSerie(
  secondKeys: string[],
  firstKeysValue: string[],
  countMap: Map<string, number>
): {
  name: string
  data: (string | number)[][]
}[] {
  const getCount = (firstKey: string, secondKey: string): number | undefined =>
    countMap.get(`${firstKey}\u0001${secondKey}`)
  if (isHistogram.value) {
    if (props.type === 'line') {
      return secondKeys.map((secondKey) => {
        const firstKeyNumbers = firstKeysValue.map((firstKey) => Number(firstKey))
        // generate all missing values
        let allFirstKeys: (number | string)[]
        if (firstKeyNumbers.some(isNaN)) {
          // TODO create date range
          allFirstKeys = clone(firstKeysValue).sort()
        } else {
          allFirstKeys = range(Math.min(...firstKeyNumbers), Math.max(...firstKeyNumbers) + 1)
        }
        let acc = 0
        const values: [number | string, number][] = allFirstKeys.map((firstKeyNumber) => {
          const count = (acc += getCount(firstKeyNumber.toString(), secondKey) ?? 0)
          return [firstKeyNumber, count]
        })
        return {
          name: secondKey,
          data: values
        }
      })
    } else {
      const binData = firstKeysValue.flatMap((firstKey) =>
        secondKeys.map((secondKey) => ({
          name: secondKey,
          value: Number(firstKey),
          count: getCount(firstKey, secondKey) ?? 0
        }))
      )
      return toBins(secondKeys, binData)
    }
  } else {
    return secondKeys.map((secondKey) => ({
      name: secondKey,
      data: firstKeysValue.map((firstKey) => [
        firstKey,
        getCount(firstKey, secondKey) ?? defaultValue.value
      ])
    }))
  }
}
function click(params: CallbackDataParams): void {
  if (props.type === 'bar') {
    if (isHistogram.value) {
      const data = params.data as BinData
      emit('change:searches', props.fields[0], `${data[2]}<<${data[3]}`)
    } else {
      emit('change:searches', props.fields[0], params.name)
    }
  }
  emit('change:searches', secondField.value, params.seriesId)
}
// The legend is a filter control, like clicking a bar of that series, not
// ECharts' default show/hide switch. ECharts has already toggled the entry by
// the time this fires, so re-select it synchronously (same tick, before paint:
// no flicker). Otherwise, once the filter leaves this as the only series, it
// would come back hidden. `legendSelect` emits `legendselected`, not this
// event, so there is no re-entry.
function legendSelectChanged(params: LegendSelectChangedParams): void {
  getInstance()?.dispatchAction({ type: 'legendSelect', name: params.name })
  emit('change:searches', secondField.value, unmapSecondName.value(params.name))
}
</script>

<template>
  <div ref="rootEl">
    <!-- Plain div, sized by CSS; ECharts is mounted imperatively (useEChart) so
         filter ticks repaint the canvas without a Vue re-render of this tile. -->
    <div ref="chartEl" class="double-chart__canvas" />
    <distribution-brush
      v-if="numberMin && numberMax"
      v-model="actualNumberRange"
      class="chart-brush"
      :series="numberSeries"
      :step="1"
      :min="roundedMin"
      :max="roundedMax"
      :bin-edges="numberBins.edges"
      :type="type"
      @dragend="onNumberDragEnd"
    />
    <date-distribution-brush
      v-if="dateMin && dateMax"
      v-model="actualDateRange"
      class="chart-brush"
      :series="dateSeries"
      :min="dateMin"
      :max="dateMax"
      :type="type"
      @dragend="onDateDragEnd"
    />
  </div>
</template>

<style scoped>
/* Breathing room between the main plot (whose x-axis name sits just inside its
   bottom edge) and the distribution brush, so the two never touch. */
.chart-brush {
  margin-top: 8px;
}

/* Match the old <v-responsive aspect-ratio="2.5" min-height="200">. The canvas
   fills this box; ResizeObserver in useEChart keeps ECharts sized to it. */
.double-chart__canvas {
  width: 100%;
  aspect-ratio: 2.5;
  min-height: 200px;
}
</style>
