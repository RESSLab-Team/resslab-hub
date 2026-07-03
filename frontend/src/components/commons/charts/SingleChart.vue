<script setup lang="ts">
import type { Count } from '@/composables/chart'
import { subscribeCrossfilter } from '@/composables/crossfilterBus'
import { useEChart } from '@/composables/useEChart'
import i18n from '@/plugins/i18n'
import type { Value } from '@/utils/common'
import { getColorPalette, primaryColor, type Color } from '@/utils/vuetify'
import { MONO, SANS } from '@/plugins/echarts-theme'
import type { EChartsOption } from 'echarts'
import { TreemapChart } from 'echarts/charts'
import { TooltipComponent } from 'echarts/components'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import type { CallbackDataParams } from 'echarts/types/dist/shared'
import { computed, onUnmounted, ref, watch } from 'vue'
import ResetChartButton from '@/components/commons/ResetChartButton.vue'

use([CanvasRenderer, TreemapChart, TooltipComponent])

const props = withDefaults(
  defineProps<{
    color?: Color
    counts?: Count[]
    field: string
    labelPrefix?: string
    flat?: boolean
    mapping?: Map<string, string>
    showReset?: boolean
    // Local (in-browser) filtering is instant, so disable ECharts animation
    // entirely — the enter/update/exit transitions otherwise read as a load and
    // cost frames on every filter tick.
    animate?: boolean
    // Client-side (crossfilter) mode: when provided, a brush drag anywhere on the
    // dashboard repaints this treemap live from the in-memory dataset via the bus,
    // off Vue's reactivity. Omitted ⇒ updates only via reactive `counts`.
    liveCounts?: (query?: string) => Count[]
  }>(),
  {
    color: () => primaryColor,
    counts: () => [],
    flat: false,
    showReset: true,
    animate: true,
    mapping: () => new Map<string, string>(),
    labelPrefix: '',
    liveCounts: undefined
  }
)
const emit = defineEmits<{
  (e: 'change:searches', key: string, value?: Value): void
  (e: 'mouseover', value: CallbackDataParams): void
  (e: 'mouseout'): void
}>()

const reverseMapping = computed(() => {
  const reverse = new Map<string, string>()
  for (const [key, value] of props.mapping.entries()) {
    reverse.set(value, key)
  }
  return reverse
})

// Plain builder shared by the reactive path and the imperative bus frames.
function buildOption(countsData: Count[]): EChartsOption {
  return {
    animation: props.animate,
    tooltip: {
      trigger: 'item',
      confine: true
    },
    series: [
      {
        type: 'treemap',
        // Treemap layout transitions ignore the root `animation` flag in ECharts
        // 5.4, so disable animation on the series itself for instant local filters.
        animation: props.animate,
        id: props.field,
        name: i18n.global.t(props.labelPrefix + props.field).toString(),
        left: 0,
        top: 0,
        right: 0,
        bottom: 0,
        data: countsData.map((count) => {
          const label = props.mapping.get(count.name) ?? count.name
          return {
            name: label,
            value: count.value,
            originalName: count.name
          }
        }),
        breadcrumb: {
          show: false
        },
        roam: false,
        // Hairline white divider between tiles: a border on each tile with no
        // gap, so neighbours share a crisp 1px seam rather than an empty channel.
        itemStyle: {
          borderColor: '#fff',
          borderWidth: 1,
          gapWidth: 0
        },
        // Label anchored top-left: bold sans name, mono count right below it
        // (handoff charts-lib.js `treemap()`), instead of ECharts' centered name.
        label: {
          show: true,
          position: 'insideTopLeft',
          padding: [7, 8],
          lineHeight: 16,
          formatter: (params: CallbackDataParams) => `{name|${params.name}}\n{value|${params.value}}`,
          rich: {
            name: {
              color: '#fff',
              fontFamily: SANS,
              fontWeight: 700,
              fontSize: 12,
              lineHeight: 16,
              align: 'left'
            },
            value: {
              color: 'rgba(255, 255, 255, 0.85)',
              fontFamily: MONO,
              fontSize: 11,
              lineHeight: 14,
              align: 'left'
            }
          }
        }
      }
    ],
    color: getColorPalette(props.color, countsData.length)
  }
}
const option = computed<EChartsOption>(() => buildOption(props.counts))

// Imperative renderer (off Vue's vnode graph); see useEChart / crossfilterBus.
const chartEl = ref<HTMLElement>()
const { render } = useEChart(chartEl, () => option.value, { click, mouseover, mouseout })

// A filter change repaints via setOption, skipped while a drag is frozen so a
// stale reactive frame can't overwrite the live one. A skipped frame is replayed
// on settle (see onSettle) so a mid-drag commit is never lost.
let frozen = false
let skippedWhileFrozen = false
watch(option, (value) => {
  if (frozen) {
    skippedWhileFrozen = true
    return
  }
  render(value)
})

// Live crossfilter: every chart repaints from the in-memory dataset during a drag,
// then reconciles on settle. No-op in server mode (no liveCounts).
let lastLiveCounts: Count[] | null = null
const unsubscribe = subscribeCrossfilter({
  onLive: (liveQuery) => {
    if (!props.liveCounts) return
    frozen = true
    lastLiveCounts = props.liveCounts(liveQuery)
    render(buildOption(lastLiveCounts))
  },
  onSettle: () => {
    if (!props.liveCounts) return
    frozen = false
    // Repaint the last drag frame (visually identical to the commit that follows,
    // so no flicker back to the pre-drag state) — unless a reactive update landed
    // mid-drag and was skipped: then the committed option is the newer truth.
    render(skippedWhileFrozen ? option.value : buildOption(lastLiveCounts ?? props.counts))
    skippedWhileFrozen = false
    lastLiveCounts = null
  }
})
onUnmounted(unsubscribe)

function click(params: CallbackDataParams): void {
  if (params.seriesId) {
    const displayedName = params.name as string
    const mappedName = props.mapping.get(displayedName)
    const originalName = reverseMapping.value.get(params.name)

    const valueToEmit = originalName || mappedName || displayedName

    emit('change:searches', params.seriesId as string, valueToEmit)
  }
}

function mouseover(params: CallbackDataParams): void {
  emit('mouseover', params)
}
function mouseout(): void {
  emit('mouseout')
}

function changeSearches(key: string, value?: Value) {
  emit('change:searches', key, value)
}
</script>

<template>
  <v-card :flat="flat">
    <v-card-title class="d-flex justify-space-between">
      <slot name="title"> </slot>
      <reset-chart-button
        v-if="showReset"
        :field="field"
        :is-filtered="counts.length === 1"
        @change:searches="changeSearches"
      />
    </v-card-title>
    <v-card-text :class="[flat ? 'pa-0' : '']">
      <!-- Plain div, CSS-sized; ECharts mounted imperatively (useEChart). -->
      <div ref="chartEl" class="single-chart__canvas" />
      <slot></slot>
    </v-card-text>
  </v-card>
</template>

<style scoped>
/* Matches the old <v-responsive min-height="100">: the treemap fills this box,
   kept sized by ResizeObserver in useEChart. */
.single-chart__canvas {
  width: 100%;
  min-height: 100px;
}
/* Chart title → card-title role (matches ChartCell's .chart-head h5), so a
   standalone chart card reads the same as a dashboard-strip chart. */
:deep(.v-card-title) {
  font-size: var(--title-card-size);
  font-weight: var(--title-card-weight);
  letter-spacing: var(--title-card-tracking);
  line-height: 1.3;
}
</style>
