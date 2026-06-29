<script setup lang="ts">
import type { CountModel } from '@/backend'
import { initOptions, updateOptions } from '@/components/commons/charts/utils'
import DateDistributionBrush from '@/components/commons/sliders/DateDistributionBrush.vue'
import DistributionBrush from '@/components/commons/sliders/DistributionBrush.vue'
import type { DoubleField, DoubleFields } from '@/composables/chart'
import i18n from '@/plugins/i18n'
import { sum, type Value } from '@/utils/common'
import { mapDateToNumber } from '@/utils/date'
import { toBins, type BinData } from '@/utils/statistics'
import type { Color } from '@/utils/vuetify'
import { getColorPalette, primaryColor } from '@/utils/vuetify'
import type { EChartsOption } from 'echarts'
import { BarChart, LineChart } from 'echarts/charts'
import {
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent
} from 'echarts/components'
import { use } from 'echarts/core'
import { SVGRenderer } from 'echarts/renderers'
import type { CallbackDataParams } from 'echarts/types/dist/shared'
import { chain, clone, range } from 'lodash'
import { computed, unref, watch } from 'vue'
import VChart from 'vue-echarts'

use([
  SVGRenderer,
  BarChart,
  LineChart,
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent
])

const props = withDefaults(
  defineProps<{
    color?: Color
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
  }>(),
  {
    color: () => primaryColor,
    allCounts: () => [],
    counts: () => [],
    dateMin: undefined,
    dateMax: undefined,
    dateRange: undefined,
    labelPrefix: '',
    numberMin: undefined,
    numberMax: undefined,
    numberRange: undefined,
    type: 'bar'
  }
)
const emit = defineEmits<{
  (e: 'change:searches', key: string, value?: Value): void
  (e: 'update:dateRange', value?: [string, string]): void
  (e: 'update:numberRange', value?: [number, number]): void
}>()

const roundedMin = computed<number>(() => Math.floor(props.numberMin ?? 0))
const roundedMax = computed<number>(() => Math.ceil(props.numberMax ?? 0))

const actualnNumberRange = computed({
  get: () => {
    if (props.numberRange !== undefined) return props.numberRange
    else if (props.numberMin !== undefined && props.numberMax !== undefined)
      return [roundedMin.value, roundedMax.value] as [number, number]
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
const firstKeys = computed<string[]>(() =>
  chain(props.counts)
    .map((count) => count.names[0])
    .uniq()
    .sort()
    .value()
)
// Index counts by (first, second) once per recompute so each grid cell is an
// O(1) lookup — getCount was scanning all counts with a deep isEqual per cell
// (≈ O(firstKeys × secondKeys × counts)). The \u0001 separator cannot appear in
// a category name, so composite keys never collide.
const countByKey = computed<Map<string, number>>(() => {
  const map = new Map<string, number>()
  for (const count of props.counts) {
    map.set(`${count.names[0]}\u0001${count.names[1]}`, count.value)
  }
  return map
})
const isHistogram = computed<boolean>(() => actualnNumberRange.value !== undefined)
// Aggregate the counts by their numeric first-key into a [value, total] shape
// that feeds the brush's distribution overview (summed across the stacked
// categories). Dates are positioned on the same day-number axis the date brush
// uses.
const numberDistribution = computed<[number, number][]>(() => {
  const totals = new Map<number, number>()
  for (const count of props.allCounts) {
    const value = Number(count.names[0])
    if (isNaN(value)) continue
    totals.set(value, (totals.get(value) ?? 0) + count.value)
  }
  return [...totals.entries()].sort((a, b) => a[0] - b[0])
})
const dateDistribution = computed<[number, number][]>(() => {
  const totals = new Map<number, number>()
  for (const count of props.allCounts) {
    const day = mapDateToNumber(count.names[0])
    if (isNaN(day)) continue
    totals.set(day, (totals.get(day) ?? 0) + count.value)
  }
  return [...totals.entries()].sort((a, b) => a[0] - b[0])
})
const option = computed<EChartsOption>(() => {
  const secondKeys: string[] = chain(props.counts)
    .groupBy((count) => count.names[1])
    .map((values, key) => ({
      key: key,
      value: values.map((count) => count.value).reduce(sum)
    }))
    .sortBy(
      (item) => -item.value,
      (item) => item.key
    )
    .map((item) => item.key)
    .value()
  const mapSecondNameValue = unref(mapSecondName)
  const option: EChartsOption = {
    title: {
      text: i18n.global.t(props.labelPrefix + secondField.value).toString(),
      textStyle: {
        fontSize: 12
      },
      left: 'center'
    },
    legend: {
      type: 'scroll',
      // Legend below the plot; line series read better with a thin line swatch,
      // bars keep the square swatch (theme default).
      bottom: 0,
      icon: 'rect',
      itemWidth: props.type === 'line' ? 18 : 10,
      itemHeight: props.type === 'line' ? 2 : 10
    },
    grid: {
      top: 40,
      bottom: 56
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
      minInterval: 1
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: props.type === 'bar' ? 'shadow' : undefined
      },
      confine: true
    },
    series: getSerie(secondKeys).map((serie) => ({
      id: serie.name,
      name: mapSecondNameValue(serie.name),
      type: props.type,
      showSymbol: serie.data.length === 1, // show symbol to avoid empty chart
      stack: secondField.value,
      areaStyle: {},
      emphasis: {
        focus: 'series'
      },
      data: serie.data
    })),
    color: getColorPalette(props.color, secondKeys.length)
  }
  return option
})

watch(actualnNumberRange, (value) => {
  let searchValue: string | undefined
  if (value && !isNaN(value[0]) && !isNaN(value[1])) {
    searchValue = `${value[0]}<<${value[1]}`
  } else {
    searchValue = undefined
  }
  //if search value equals to min/max value, then there's no search value
  if (props.numberMin !== undefined && props.numberMax !== undefined) {
    if (value && value[0] === roundedMin.value && value[1] === roundedMax.value) {
      searchValue = undefined
    }
  }
  emit('change:searches', props.fields[0], searchValue)
})
watch(actualDateRange, (value) => {
  let searchValue: string | undefined
  if (value) {
    searchValue = `${value[0]}<<${value[1]}`
  } else {
    searchValue = undefined
  }

  //if search value equals to min/max value, then there's no search value
  if (props.dateMin !== undefined && props.dateMax !== undefined) {
    if (value && value[0] === props.dateMin && value[1] === props.dateMax) {
      searchValue = undefined
    }
  }

  emit('change:searches', props.fields[0], searchValue)
})

function getSerie(secondKeys: string[]): {
  name: string
  data: (string | number)[][]
}[] {
  const firstKeysValue = unref(firstKeys)
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
function getCount(firstKey: string, secondKey: string): number | undefined {
  return countByKey.value.get(`${firstKey}\u0001${secondKey}`)
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
</script>

<template>
  <div>
    <v-responsive aspect-ratio="2.5" min-height="200">
      <v-chart
        autoresize
        :init-options="initOptions"
        :option="option"
        :update-options="updateOptions"
        @click="click"
      />
    </v-responsive>
    <distribution-brush
      v-if="numberMin && numberMax"
      v-model="actualnNumberRange"
      :color="color"
      :distribution="numberDistribution"
      :step="1"
      :min="roundedMin"
      :max="roundedMax"
      :type="type"
    />
    <date-distribution-brush
      v-if="dateMin && dateMax"
      v-model="actualDateRange"
      :color="color"
      :distribution="dateDistribution"
      :min="dateMin"
      :max="dateMax"
      :type="type"
    />
  </div>
</template>
