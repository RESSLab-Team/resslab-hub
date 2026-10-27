<script setup lang="ts">
import UnitChart from '@/components/commons/charts/UnitChart.vue'
import { primaryColors, type Color } from '@/utils/vuetify'
import type { EChartsOption, LineSeriesOption } from 'echarts'
import { TitleComponent } from 'echarts/components'
import { use } from 'echarts/core'
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
    fill?: boolean
    /** Legend on the right instead of below the plot. Left unset, a chart
        with more than 2 series gets it; a small card passes false, since the
        side legend takes 200px off the plot. */
    legendSide?: boolean
  }>(),
  {
    colors: () => primaryColors,
    series: () => [],
    aspectRatio: 1,
    axisPointerType: 'x',
    fill: false,
    maxWidth: undefined,
    title: undefined,
    xAxisName: undefined,
    yAxisName: undefined,
    xUnit: undefined,
    yUnit: undefined,
    xAxisMin: undefined,
    yAxisMin: undefined,
    xAxisMax: undefined,
    yAxisMax: undefined,
    legendSide: undefined
  }
)

use([TitleComponent])

const option = computed<EChartsOption>(
  () =>
    ({
      title: {
        text: props.title,
        left: 'center'
      },
      // Leave headroom for the title when present; otherwise inherit UnitChart's
      // compact top (legend now lives below the plot, not above it).
      grid: {
        top: props.title ? 36 : undefined
      },
      legend: {
        show: props.series.length > 1
      },
      xAxis: {
        name: props.xAxisName,
        min: props.xAxisMin,
        max: props.xAxisMax
      },
      yAxis: {
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
      // Spread rather than `merge`: the callers' `data` arrays run to thousands
      // of points and a deep merge would clone every one of them on each update.
      // Only `lineStyle` actually needs merging with the default.
      series: props.series.map((serie) => ({
        type: 'line',
        showSymbol: false,
        ...serie,
        lineStyle: { width: 1, ...serie.lineStyle }
      })),
      color: props.colors.map((color) => color.base)
    } as EChartsOption)
)
</script>

<template>
  <unit-chart
    :aspect-ratio="aspectRatio"
    :fill="fill"
    :legend-side="legendSide ?? props.series.length > 2"
    :max-width="maxWidth"
    :option="option"
    :x-unit="xUnit"
    :y-unit="yUnit"
  />
</template>
