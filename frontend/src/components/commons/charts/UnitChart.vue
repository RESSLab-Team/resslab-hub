<script setup lang="ts">
import { initOptions, updateOptions } from '@/components/commons/charts/utils'
import { useUnits } from '@/composables/unit'
import type { EChartsOption, SeriesOption, TooltipComponentFormatterCallbackParams } from 'echarts'
import { LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { use } from 'echarts/core'
import { SVGRenderer } from 'echarts/renderers'
import type { XAXisOption, YAXisOption } from 'echarts/types/dist/shared'
import { cloneDeep, merge, round } from 'lodash'
import { computed, withDefaults } from 'vue'
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
  }>(),
  {
    xUnit: undefined,
    yUnit: undefined,
    aspectRatio: 1,
    maxWidth: undefined,
    legendSide: false
  }
)

const axisLabelMaxDigits = 2

const { ratio: xRatio, unitLabel: xUnitLabel } = useUnits(props.xUnit)
const { ratio: yRatio, unitLabel: yUnitLabel } = useUnits(props.yUnit)

const actualOption = computed<EChartsOption>(() => {
  const option = cloneDeep(props.option)
  const xAXisOption: XAXisOption = option.xAxis as XAXisOption
  const yAXisOption: YAXisOption = option.yAxis as YAXisOption
  const defaultOption: EChartsOption = {
    grid: {
      left: 60,
      top: 40,
      right: props.legendSide ? 180 : 20,
      bottom: 40
    },
    legend: {
      type: 'scroll',
      top: 0,
      right: props.legendSide ? 0 : undefined,
      orient: props.legendSide ? 'vertical' : 'horizontal'
    },
    xAxis: {
      nameLocation: 'middle',
      nameTextStyle: {
        fontWeight: 'bold'
      },
      nameGap: 26,
      max: xAXisOption?.max ?? 'dataMax',
      axisLabel: {
        formatter: (value: number) => `${round(value, axisLabelMaxDigits)}`,
        hideOverlap: true
      }
    },
    yAxis: {
      nameLocation: 'middle',
      nameTextStyle: {
        fontWeight: 'bold'
      },
      nameGap: 50,
      max: yAXisOption?.max ?? 'dataMax',
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
  const overrideOption: EChartsOption = {
    xAxis: {
      name: props.xUnit ? `${xAXisOption.name} [${xUnitLabel.value}]` : xAXisOption.name
    },
    yAxis: {
      name: props.yUnit ? `${yAXisOption.name} [${yUnitLabel.value}]` : yAXisOption.name
    },
    series: (option.series as SeriesOption[]).map((serie) =>
      merge(serie, {
        data: (serie.data as [number, number][]).map((v) => [
          v[0] / xRatio.value,
          v[1] / yRatio.value
        ])
      })
    )
  }
  return merge(defaultOption, option, overrideOption)
})
</script>

<template>
  <v-responsive :aspect-ratio="aspectRatio" :max-width="maxWidth">
    <v-chart
      autoresize
      :init-options="initOptions"
      :option="actualOption"
      :update-options="updateOptions"
    />
  </v-responsive>
</template>
