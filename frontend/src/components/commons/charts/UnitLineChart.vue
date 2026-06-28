<script setup lang="ts">
import UnitChart from '@/components/commons/charts/UnitChart.vue'
import { primaryColors, type Color } from '@/utils/vuetify'
import type { EChartsOption, LineSeriesOption } from 'echarts'
import { TitleComponent } from 'echarts/components'
import { use } from 'echarts/core'
import { merge } from 'lodash'
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    colors?: Color[]
    series?: LineSeriesOption[]
    aspectRatio?: number
    axisPointerType?: string
    maxWidth?: number
    title?: string
    xAxisName: string
    yAxisName: string
    xUnit?: string
    yUnit?: string
    xAxisMin?: number
    yAxisMin?: number
    xAxisMax?: number
    yAxisMax?: number
  }>(),
  {
    colors: () => primaryColors,
    series: () => [],
    aspectRatio: 1,
    axisPointerType: 'x',
    maxWidth: undefined,
    title: undefined,
    xAxisName: undefined,
    yAxisName: undefined,
    xUnit: undefined,
    yUnit: undefined,
    xAxisMin: undefined,
    yAxisMin: undefined,
    xAxisMax: undefined,
    yAxisMax: undefined
  }
)

use([TitleComponent])

// ECharts reads a literal font string (CSS vars don't resolve); mirror the
// mono stack + muted ink from epfl-tokens.css for the axis-name labels.
const MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Monaco, Consolas, monospace"
const NAME = '#6e6e73' // muted axis-name ink

// Keep the gridded layout + default name placement; only restyle the axis names
// to mono grey so they sit quieter against the data.
const responseAxis = {
  nameTextStyle: { color: NAME, fontFamily: MONO, fontWeight: 'normal' as const, fontSize: 11 }
}

const option = computed<EChartsOption>(
  () =>
    ({
      title: {
        text: props.title,
        left: 'center'
      },
      grid: {
        //If there are more than 2 series, the legend will be on the right so we don't need to leave more space for it
        top: props.series.length > 2 ? 40 : 60
      },
      legend: {
        top: 30,
        show: props.series.length > 1
      },
      xAxis: {
        ...responseAxis,
        name: props.xAxisName,
        min: props.xAxisMin,
        max: props.xAxisMax
      },
      yAxis: {
        ...responseAxis,
        name: props.yAxisName,
        min: props.yAxisMin,
        max: props.yAxisMax
      },
      tooltip: {
        formatter: null as unknown as undefined,
        axisPointer: {
          axis: props.axisPointerType
        }
      },
      series: props.series.map((serie) =>
        merge<LineSeriesOption, LineSeriesOption>(
          {
            type: 'line',
            showSymbol: false,
            lineStyle: {
              width: 1
            }
          },
          serie
        )
      ),
      color: props.colors.map((color) => color.base)
    } as EChartsOption)
)
</script>

<template>
  <unit-chart
    :aspect-ratio="aspectRatio"
    :legend-side="props.series.length > 2"
    :max-width="maxWidth"
    :option="option"
    :x-unit="xUnit"
    :y-unit="yUnit"
  />
</template>
