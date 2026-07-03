<script setup lang="ts">
import { initOptions, updateOptions } from '@/components/commons/charts/utils'
import { useUnits } from '@/composables/unit'
import type { EChartsOption, SeriesOption, TooltipComponentFormatterCallbackParams } from 'echarts'
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
    // Fill the parent's height instead of locking to `aspectRatio`. Use inside a
    // height-bounded flex container (the fit-in-viewport tool pages) so the chart
    // tracks the available height rather than growing with its column width.
    fit?: boolean
  }>(),
  {
    xUnit: undefined,
    yUnit: undefined,
    aspectRatio: 1,
    maxWidth: undefined,
    legendSide: false,
    fit: false
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
      left: 60,
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
      // Axis-name styling (grey/mono/regular) comes from the global theme.
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
      nameGap: 50,
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
  merged.series = (series as SeriesOption[] | undefined)?.map(
    (serie) =>
      ({
        ...serie,
        data: (serie.data as [number, number][] | undefined)?.map((v): [number, number] => [
          v[0] / xRatio.value,
          v[1] / yRatio.value
        ])
      } as SeriesOption)
  )
  return merged
})
</script>

<template>
  <div v-if="fit" class="uc-fill">
    <div class="uc-wrap">
      <v-chart
        autoresize
        :init-options="initOptions"
        :option="actualOption"
        :update-options="updateOptions"
      />
      <span v-if="showLegendRule" class="uc-legend-rule" />
    </div>
  </div>
  <v-responsive v-else :aspect-ratio="aspectRatio" :max-width="maxWidth">
    <div class="uc-wrap">
      <v-chart
        autoresize
        :init-options="initOptions"
        :option="actualOption"
        :update-options="updateOptions"
      />
      <span v-if="showLegendRule" class="uc-legend-rule" />
    </div>
  </v-responsive>
</template>

<style scoped>
/* Fill mode: take the full height the flex parent grants us (min-height:0 lets
   the box shrink below the chart's intrinsic size). vue-echarts' root is
   100%×100%, so the canvas tracks this box via `autoresize`. */
.uc-fill {
  width: 100%;
  height: 100%;
  min-height: 0;
}
.uc-wrap {
  position: relative;
  width: 100%;
  height: 100%;
}
/* Hairline that fences the bottom legend off from the plot + x-axis label
   (handoff). Offsets track the grid (left 60 / right 20) and the legend band —
   all fixed in px, so the rule stays put at any chart height. */
.uc-legend-rule {
  position: absolute;
  left: 60px;
  right: 20px;
  bottom: 32px;
  border-top: 1px solid var(--border);
  pointer-events: none;
}
</style>
