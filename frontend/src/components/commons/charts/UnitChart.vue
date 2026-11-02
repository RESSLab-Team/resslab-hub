<script setup lang="ts">
import { initOptions } from '@/components/commons/charts/utils'
import { useUnits } from '@/composables/unit'
import type {
  EChartsOption,
  SeriesOption,
  SetOptionOpts,
  TooltipComponentFormatterCallbackParams
} from 'echarts'
import { LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { use } from 'echarts/core'
import { SVGRenderer } from 'echarts/renderers'
import type { XAXisOption, YAXisOption } from 'echarts/types/dist/shared'
import { merge, round } from 'lodash'
import { computed } from 'vue'
import VChart from 'vue-echarts'

use([SVGRenderer, LineChart, GridComponent, LegendComponent, TooltipComponent])

const props = withDefaults(
  defineProps<{
    option: EChartsOption
    xUnit?: string
    yUnit?: string
    aspectRatio?: number
    maxWidth?: number
    legendSide?: boolean
    /** Fill the parent's height instead of sizing by aspect ratio.
        Used by the Rail+Stage tool layout, where the containing block
        sets an explicit height (.h-chart / grid cell) and ECharts tracks it. */
    fill?: boolean
  }>(),
  {
    xUnit: undefined,
    yUnit: undefined,
    aspectRatio: 1,
    maxWidth: undefined,
    legendSide: false,
    fill: false
  }
)

const axisLabelMaxDigits = 2

// Moment charts reach 7-digit kN⋅mm values, and a label like "2000000" runs
// into the rotated axis name. When an axis goes past 100 000, every label on
// it is written short ("500K", "1.5M"), so one axis never mixes both forms.
const compactNumber = new Intl.NumberFormat('en', {
  notation: 'compact',
  maximumFractionDigits: 2
})
const compactFrom = 1e5

/** Largest absolute value of coordinate `index` over every series, in the
    unit shown on screen (the raw value divided by `ratio`). */
function absMax(series: SeriesOption[] | undefined, index: 0 | 1, ratio: number): number {
  let max = 0
  for (const serie of series ?? []) {
    for (const point of (serie.data as [number, number][] | undefined) ?? []) {
      const value = Math.abs(point[index] / ratio)
      if (value > max) max = value
    }
  }
  return max
}

function axisLabelFormatter(compact: boolean) {
  return compact
    ? (value: number) => compactNumber.format(value)
    : (value: number) => `${round(value, axisLabelMaxDigits)}`
}

// The legend swatch is a flat 18x2 rectangle, so a dashed series (a model
// drawn over measured data) looks solid in it. This path is that same
// rectangle cut into three dashes; ECharts scales it to itemWidth x itemHeight
// and fills it with the series colour, like the plain `rect`.
const DASHED_SWATCH = 'path://M0,0h5v2h-5z M6.5,0h5v2h-5z M13,0h5v2h-5z'

/** Legend entries in series order, with a dashed swatch for dashed series. */
function legendData(series: SeriesOption[] | undefined) {
  return (series ?? [])
    .filter((serie) => serie.name !== undefined)
    .map((serie) => {
      const lineStyle = (serie as { lineStyle?: { type?: unknown } }).lineStyle
      return lineStyle?.type === 'dashed'
        ? { name: String(serie.name), icon: DASHED_SWATCH }
        : { name: String(serie.name) }
    })
}

const { ratio: xRatio, unitLabel: xUnitLabel } = useUnits(props.xUnit)
const { ratio: yRatio, unitLabel: yUnitLabel } = useUnits(props.yUnit)

// A bottom legend (multi-series, not the right-rail variant) gets a hairline
// fence and extra padding below the x-axis label; single-series charts don't.
const seriesCount = computed(() => {
  const s = props.option.series
  return Array.isArray(s) ? s.length : s ? 1 : 0
})
const showLegendRule = computed(() => !props.legendSide && seriesCount.value > 1)

const actualOption = computed<EChartsOption>(() => {
  const xAXisOption: XAXisOption = props.option.xAxis as XAXisOption
  const yAXisOption: YAXisOption = props.option.yAxis as YAXisOption
  const allSeries = props.option.series as SeriesOption[] | undefined
  const compactX = absMax(allSeries, 0, xRatio.value) >= compactFrom
  const compactY = absMax(allSeries, 1, yRatio.value) >= compactFrom
  const defaultOption: EChartsOption = {
    grid: {
      // The rotated y-axis name sits at `left - nameGap` from the container
      // edge (74 - 44 = 30px), while `nameGap` itself is what keeps the name
      // clear of the tick labels. The moment charts render 6-digit kN⋅mm
      // labels ~40px wide, so nameGap has little room to shrink further.
      left: 74,
      top: props.legendSide ? 10 : 16,
      right: props.legendSide ? 200 : 20,
      // Reserve a legend band only when the legend actually sits below the plot.
      bottom: props.legendSide ? 40 : showLegendRule.value ? 78 : 40
    },
    legend: {
      type: 'scroll',
      // Legend sits below the plot (handoff); many-series charts keep a vertical
      // legend on the right. A thin, wide swatch reads as a line — not a square —
      // which suits these line charts.
      ...(props.legendSide
        ? { top: 80, right: 0, orient: 'vertical' as const }
        : { bottom: 4, left: 'center' as const, orient: 'horizontal' as const }),
      icon: 'rect',
      itemWidth: 18,
      itemHeight: 2
    },
    xAxis: {
      // Axis-name styling (grey/regular) comes from the global theme.
      nameLocation: 'middle',
      nameGap: 26,
      max: xAXisOption?.max,
      axisLabel: {
        formatter: axisLabelFormatter(compactX),
        hideOverlap: true
      }
    },
    yAxis: {
      // Name rides along the axis (rotated, mid-height) — never above the plot.
      nameLocation: 'middle',
      nameGap: 44,
      max: yAXisOption?.max,
      axisLabel: {
        formatter: axisLabelFormatter(compactY),
        hideOverlap: true
      }
    },
    tooltip: {
      trigger: 'axis',
      confine: true,
      valueFormatter: (value) => (value as number).toFixed(2),
      formatter: (params: TooltipComponentFormatterCallbackParams) => {
        if (!Array.isArray(params)) {
          return ''
        }
        const value = (params[0].value as number[])[0].toFixed(2)
        const suffix = props.yUnit ? ` [${yUnitLabel.value}]` : ''
        return [
          `<b>${xAXisOption?.name?.split(', ')[0]}: ${value} [${xUnitLabel.value}]</b>`,
          ...params
            .map((param) => {
              if (Array.isArray(param.value)) {
                const value = param.value[1] as number
                const displayValue = value.toFixed(2)
                return value !== 0
                  ? `${param.marker} ${param.seriesName}: ${displayValue}` + suffix
                  : ''
              }
              return `${param.value}`
            })
            .filter((text) => text.length > 0)
        ].join('<br />')
      }
    }
  }

  // Merge the caller's config over the defaults WITHOUT the series, so the
  // (potentially large) data arrays are never deep-cloned or deep-merged.
  const { series, ...rest } = props.option
  const merged = merge(defaultOption, rest, {
    xAxis: {
      name: props.xUnit ? `${xAXisOption.name} [${xUnitLabel.value}]` : xAXisOption.name
    },
    yAxis: {
      name: props.yUnit ? `${yAXisOption.name} [${yUnitLabel.value}]` : yAXisOption.name
    }
  }) as EChartsOption

  // Named entries so the legend keeps the callers' series order across
  // updates (a merged setOption appends new series after the old ones) and so
  // a dashed series gets a dashed swatch.
  merged.legend = { ...(merged.legend as object), data: legendData(series as SeriesOption[]) }

  // Scale every point exactly once into fresh arrays; never mutate props.option.
  // Every series also gets a stable id so ECharts can map the incoming series
  // onto the ones already rendered and update them in place (see below).
  merged.series = (series as SeriesOption[] | undefined)?.map(
    (serie, index) =>
      ({
        id: serie.id ?? serie.name ?? `s${index}`,
        ...serie,
        data: (serie.data as [number, number][] | undefined)?.map((v): [number, number] => [
          v[0] / xRatio.value,
          v[1] / yRatio.value
        ])
      } as SeriesOption)
  )
  return merged
})

// Size of the aspect-ratio box (non-fill mode).
const boxStyle = computed(() => ({
  aspectRatio: String(props.aspectRatio),
  maxWidth: props.maxWidth !== undefined ? `${props.maxWidth}px` : undefined
}))

// How each `setOption` is applied. `replaceMerge: ['series']` tears every series
// component down and rebuilds it — the chart replays its entry animation, which
// is what makes a slider drag look like a full redraw. It's only needed when the
// SET of series changes (a panel switch dropping a curve would otherwise leave a
// stale one behind). So compare the series ids against the previous render and
// pay for the replace only then; steady-state updates — a slider moving a curve —
// merge in place and animate as a data transition.
//
// `previousSeriesKey` is a plain (non-reactive) per-instance variable: this
// computed is invalidated exactly when `actualOption` changes, and vue-echarts
// reads it while handling that same change, so the two stay in step.
let previousSeriesKey: string | null = null
const chartUpdateOptions = computed<SetOptionOpts>(() => {
  const key = ((actualOption.value.series as SeriesOption[] | undefined) ?? [])
    .map((serie) => serie.id)
    .join('|')
  const seriesSetChanged = key !== previousSeriesKey
  previousSeriesKey = key
  return seriesSetChanged ? { notMerge: false, replaceMerge: ['series'] } : { notMerge: false }
})
</script>

<template>
  <div v-if="fill" class="uc-wrap uc-fill">
    <v-chart
      autoresize
      :init-options="initOptions"
      :option="actualOption"
      :update-options="chartUpdateOptions"
    />
    <span v-if="showLegendRule" class="uc-legend-rule" />
  </div>
  <div v-else class="uc-box" :style="boxStyle">
    <div class="uc-wrap">
      <v-chart
        autoresize
        :init-options="initOptions"
        :option="actualOption"
        :update-options="chartUpdateOptions"
      />
      <span v-if="showLegendRule" class="uc-legend-rule" />
    </div>
  </div>
</template>

<style scoped>
/* A plain box with CSS aspect-ratio, not a <v-responsive>. v-responsive puts
   its content over its sizer with a -100% margin, and when the Vuetify reset
   layer wins over that margin the chart draws at half width, on the right
   half of its box (#385). Here nothing depends on the layer order. */
.uc-box {
  width: 100%;
  margin-inline: auto;
}
.uc-wrap {
  position: relative;
  width: 100%;
  height: 100%;
}
/* Fill mode: the wrapper takes the block's full height (no aspect-ratio box);
   vue-echarts autoresize tracks the container. */
.uc-fill {
  min-height: 0;
}
.uc-fill > :deep(.echarts) {
  width: 100%;
  height: 100%;
}
/* Hairline that fences the bottom legend off from the plot + x-axis label
   (handoff). Offsets track the grid (left 74 / right 20) and the legend band —
   all fixed in px, so the rule stays put at any chart height. */
.uc-legend-rule {
  position: absolute;
  left: 74px;
  right: 20px;
  bottom: 32px;
  border-top: 1px solid var(--border);
  pointer-events: none;
}
</style>
