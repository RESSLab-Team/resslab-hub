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
    fit?: boolean
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
    fit: false,
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
    :fit="fit"
    :legend-side="props.series.length > 2"
    :max-width="maxWidth"
    :option="option"
    :x-unit="xUnit"
    :y-unit="yUnit"
  />
</template>
