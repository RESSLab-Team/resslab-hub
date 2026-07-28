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
        formatter: (value: number) => `${round(value, axisLabelMaxDigits)}`,
        hideOverlap: true
      }
    },
    yAxis: {
      // Name rides along the axis (rotated, mid-height) — never above the plot.
      nameLocation: 'middle',
      nameGap: 44,
      max: yAXisOption?.max,
      axisLabel: {
        formatter: (value: number) => `${round(value, axisLabelMaxDigits)}`,
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
  <v-responsive v-else :aspect-ratio="aspectRatio" :max-width="maxWidth">
    <div class="uc-wrap">
      <v-chart
        autoresize
        :init-options="initOptions"
        :option="actualOption"
        :update-options="chartUpdateOptions"
      />
      <span v-if="showLegendRule" class="uc-legend-rule" />
    </div>
  </v-responsive>
</template>

<style scoped>
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
