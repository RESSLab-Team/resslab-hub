<script setup lang="ts">
/**
 * A "context" range filter: a slim overview of the whole distribution with two
 * draggable handles that define the active window — the focus+context idiom
 * from Observable/Tableau. Built on an ECharts `dataZoom` slider whose
 * `dataBackground` draws the full distribution faintly and whose
 * `selectedDataBackground` highlights the part inside the window.
 *
 * The x-axis spans the *stable* full extent [min, max] (the data bounds, which
 * don't shrink when a filter is applied), so the handles always have room to be
 * dragged back out. The flanking number inputs keep precise values typeable.
 */
import { useColor } from '@/composables/color'
import { initOptions } from '@/components/commons/charts/utils'
import type { Color } from '@/utils/vuetify'
import type { EChartsOption } from 'echarts'
import { BarChart, LineChart } from 'echarts/charts'
import { DataZoomComponent, GridComponent } from 'echarts/components'
import { use } from 'echarts/core'
import { SVGRenderer } from 'echarts/renderers'
import { computed } from 'vue'
import VChart from 'vue-echarts'

use([SVGRenderer, LineChart, BarChart, GridComponent, DataZoomComponent])

const props = withDefaults(
  defineProps<{
    modelValue?: [number, number]
    min: number
    max: number
    // The distribution shape as [value, count] pairs, sorted by value.
    distribution?: [number, number][]
    step?: number
    color?: Color
    type?: 'bar' | 'line'
    // Render the handle/bound values through a formatter (used by the date variant).
    formatter?: (value: number) => string
  }>(),
  {
    modelValue: undefined,
    distribution: () => [],
    step: 1,
    color: undefined,
    type: 'bar',
    formatter: undefined
  }
)
const emit = defineEmits<{
  (e: 'update:modelValue', value: [number, number]): void
}>()

const { baseColor, darkenColor } = useColor(props.color)

const actualMin = computed<number>(() => props.min - (props.min % props.step))
const actualMax = computed<number>(() => Math.ceil(props.max / props.step) * props.step)
const span = computed<number>(() => Math.max(actualMax.value - actualMin.value, props.step))

const range = computed<[number, number]>({
  get: () => props.modelValue ?? [actualMin.value, actualMax.value],
  set: (value) =>
    emit('update:modelValue', [
      Math.max(actualMin.value, value[0]),
      Math.min(actualMax.value, value[1])
    ])
})

// Handle positions as percentages of the stable [min, max] extent.
const startEnd = computed<[number, number]>(() => {
  const [lo, hi] = range.value
  const toPct = (v: number) => ((v - actualMin.value) / span.value) * 100
  return [toPct(lo), toPct(hi)]
})

function rgba(hex: string | undefined, alpha: number): string {
  if (!hex) return `rgba(0,0,0,${alpha})`
  const h = hex.replace('#', '')
  const full =
    h.length === 3
      ? h
          .split('')
          .map((c) => c + c)
          .join('')
      : h
  const n = parseInt(full, 16)
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${alpha})`
}

const option = computed<EChartsOption>(() => {
  const isLine = props.type === 'line'
  return {
    animation: false,
    grid: { left: 2, right: 2, top: 4, bottom: 4 },
    xAxis: [
      {
        // Visible axis — series renders here; range is fixed so it never zooms.
        type: 'value',
        min: actualMin.value,
        max: actualMax.value,
        show: false,
        boundaryGap: !isLine
      },
      {
        // Hidden axis — hosts the dataZoom slider so its geometry works,
        // but zooming this axis clips nothing because no series maps to it.
        type: 'value',
        min: actualMin.value,
        max: actualMax.value,
        show: false
      }
    ],
    yAxis: { type: 'value', show: false },
    series: [
      {
        // Visible distribution shape (bars or area).
        type: props.type,
        xAxisIndex: 0,
        smooth: isLine,
        symbol: isLine ? 'none' : undefined,
        silent: true,
        ...(isLine
          ? {
              lineStyle: { width: 0 },
              areaStyle: { color: rgba(baseColor.value, 0.45) }
            }
          : {
              barWidth: '80%',
              itemStyle: {
                color: rgba(baseColor.value, 0.55)
              }
            }),
        data: props.distribution
      },
      {
        // Hidden series on the dataZoom axis — gives the slider the geometry
        // it needs to render handles, even though it's visually invisible.
        type: 'line',
        xAxisIndex: 1,
        smooth: false,
        symbol: 'none',
        silent: true,
        lineStyle: { color: 'transparent', width: 0 },
        areaStyle: { opacity: 0 },
        data: props.distribution
      }
    ],
    dataZoom: [
      {
        type: 'slider',
        // Attach to the hidden second axis so slider handles render
        // correctly, but zooming it has no visual effect on anything.
        xAxisIndex: 1,
        filterMode: 'none',
        realtime: true,
        showDataShadow: false,
        showDetail: false,
        left: 2,
        right: 2,
        top: 0,
        bottom: 0,
        height: '100%',
        start: startEnd.value[0],
        end: startEnd.value[1],
        backgroundColor: 'transparent',
        borderColor: 'transparent',
        dataBackground: {
          lineStyle: { opacity: 0 },
          areaStyle: { opacity: 0 }
        },
        selectedDataBackground: {
          lineStyle: { opacity: 0 },
          areaStyle: { opacity: 0 }
        },
        fillerColor: rgba(baseColor.value, 0.15),
        handleSize: '110%',
        handleStyle: {
          color: '#fff',
          borderColor: darkenColor.value,
          borderWidth: 1,
          shadowBlur: 3,
          shadowColor: 'rgba(0,0,0,0.2)'
        },
        moveHandleSize: 5,
        moveHandleStyle: { color: rgba(darkenColor.value, 0.6) },
        brushSelect: false
      }
    ]
  }
})

function onZoom(params: unknown): void {
  // vue-echarts forwards the raw datazoom event; single-zoom payloads carry
  // start/end directly, batched ones nest them under `batch[0]`.
  const p = params as { start?: number; end?: number; batch?: { start: number; end: number }[] }
  const z = p.batch?.[0] ?? p
  if (z.start === undefined || z.end === undefined) return
  const snap = (pct: number) => {
    const raw = actualMin.value + (pct / 100) * span.value
    return Math.round(raw / props.step) * props.step
  }
  const next: [number, number] = [snap(z.start), snap(z.end)]
  if (next[0] !== range.value[0] || next[1] !== range.value[1]) {
    range.value = next
  }
}

const fieldClass = 'mt-0 pt-0'
function onMinChanged(event: Event): void {
  range.value = [Number((event.target as HTMLInputElement).value), range.value[1]]
}
function onMaxChanged(event: Event): void {
  range.value = [range.value[0], Number((event.target as HTMLInputElement).value)]
}
const displayMin = computed(() =>
  props.formatter ? props.formatter(range.value[0]) : range.value[0]
)
const displayMax = computed(() =>
  props.formatter ? props.formatter(range.value[1]) : range.value[1]
)
</script>

<template>
  <div class="dist-brush">
    <v-text-field
      v-if="!formatter"
      :class="fieldClass"
      density="compact"
      hide-details
      :max="actualMax"
      :min="actualMin"
      :model-value="range[0]"
      single-line
      type="number"
      variant="underlined"
      @change="onMinChanged"
    />
    <span v-else class="dist-brush__bound">{{ displayMin }}</span>
    <v-chart
      class="dist-brush__chart"
      :init-options="initOptions"
      :option="option"
      :update-options="{ notMerge: false }"
      autoresize
      @datazoom="onZoom"
    />
    <v-text-field
      v-if="!formatter"
      :class="fieldClass"
      density="compact"
      hide-details
      :max="actualMax"
      :min="actualMin"
      :model-value="range[1]"
      single-line
      type="number"
      variant="underlined"
      @change="onMaxChanged"
    />
    <span v-else class="dist-brush__bound">{{ displayMax }}</span>
  </div>
</template>

<style scoped>
.dist-brush {
  display: flex;
  align-items: center;
  gap: 8px;
}
.dist-brush__chart {
  flex: 1 1 auto;
  height: 40px;
}
.dist-brush :deep(.v-text-field) {
  flex: 0 0 60px;
  width: 60px;
}
.dist-brush__bound {
  flex: 0 0 auto;
  min-width: 60px;
  font-size: 0.8125rem;
  font-variant-numeric: tabular-nums;
  color: rgba(0, 0, 0, 0.7);
  text-align: center;
}
</style>
