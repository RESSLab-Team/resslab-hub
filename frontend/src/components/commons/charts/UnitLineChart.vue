<script setup lang="ts">
import UnitChart from '@/components/commons/charts/UnitChart.vue'
import { primaryColor, secondaryColor, type Color } from '@/utils/vuetify'
import type { EChartsOption, LineSeriesOption } from 'echarts'
import { TitleComponent } from 'echarts/components'
import { use } from 'echarts/core'
import { merge } from 'lodash'
import { computed, withDefaults } from 'vue'

const props = withDefaults(
  defineProps<{
    colors?: Color[]
    series?: LineSeriesOption[]
    aspectRatio?: number
    maxWidth?: number
    title: string
    xAxisName: string
    yAxisName: string
    xUnit?: string
    yUnit?: string
  }>(),
  {
    colors: () => [primaryColor, secondaryColor],
    series: () => [],
    aspectRatio: 1,
    maxWidth: undefined,
    title: undefined,
    xAxisName: undefined,
    yAxisName: undefined,
    xUnit: undefined,
    yUnit: undefined
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
      grid: {
        top: 60
      },
      legend: {
        top: 30,
        show: props.series.length > 1
      },
      xAxis: {
        name: props.xAxisName
      },
      yAxis: {
        name: props.yAxisName
      },
      tooltip: {
        formatter: null as unknown as undefined
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
    :max-width="maxWidth"
    :option="option"
    :x-unit="xUnit"
    :y-unit="yUnit"
  />
</template>
