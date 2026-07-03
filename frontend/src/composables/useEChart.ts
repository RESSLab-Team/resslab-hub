/**
 * Imperative ECharts binding — the elegant alternative to vue-echarts' reactive
 * `:option` prop for charts on the client-side filter hot path.
 *
 * WHY THIS EXISTS
 * ---------------
 * `<v-chart :option="option">` makes the ECharts option a *reactive Vue prop*.
 * Every filter tick then rebuilds the option, re-renders the host component's
 * vnodes, diffs them through vue-echarts, and only then calls `setOption`. With
 * ~8 charts cross-filtering at once that cascade collapses into one `flushJobs`
 * long task — the reconciliation, not the d3 filtering, was the lag.
 *
 * This composable takes ECharts *off* the Vue render graph: it owns the instance
 * and exposes a plain `render(option)`. The host decides when to call it — from a
 * guarded `watch` for normal filter changes, or straight from the crossfilter bus
 * during a drag (no reactivity at all). Same idea as the classic d3/crossfilter
 * dashboards: recompute, then imperatively repaint.
 */
import { canvasInitOptions, updateOptions } from '@/components/commons/charts/utils'
import { echartsTheme } from '@/plugins/echarts-theme'
import type { EChartsOption } from 'echarts'
import { init } from 'echarts/core'
import type { CallbackDataParams } from 'echarts/types/dist/shared'
import { onBeforeUnmount, onMounted, type Ref } from 'vue'

export type EChartHandlers = Partial<
  Record<'click' | 'mouseover' | 'mouseout', (params: CallbackDataParams) => void>
>

/**
 * Mount an ECharts instance on `el` and return an imperative `render`.
 *
 * @param el        the container element (a plain <div>, sized by CSS)
 * @param initial   builds the option for the first paint on mount
 * @param handlers  optional event handlers (currently just `click`)
 */
export function useEChart(
  el: Ref<HTMLElement | undefined>,
  initial: () => EChartsOption,
  handlers: EChartHandlers = {}
) {
  let chart: ReturnType<typeof init> | undefined
  let resizeObserver: ResizeObserver | undefined

  /** Diff-merge an option into the live instance. No-op before mount / after dispose. */
  function render(option: EChartsOption): void {
    chart?.setOption(option, updateOptions)
  }

  onMounted(() => {
    if (!el.value) return
    // init from echarts/core (not `echarts`) so the tree-shaken registration the
    // host declares via `use([...])` applies; theme + canvas renderer match what
    // vue-echarts did via THEME_KEY / canvasInitOptions.
    chart = init(el.value, echartsTheme, canvasInitOptions)
    for (const [event, handler] of Object.entries(handlers)) {
      chart.on(event, (params) => handler(params as CallbackDataParams))
    }
    render(initial())

    // rAF-guard the resize so a layout-triggered observer callback can't spin the
    // "ResizeObserver loop limit exceeded" warning.
    resizeObserver = new ResizeObserver(() => {
      requestAnimationFrame(() => chart?.resize())
    })
    resizeObserver.observe(el.value)
  })

  onBeforeUnmount(() => {
    resizeObserver?.disconnect()
    // Detach handlers before dispose so a callback queued mid-teardown can't
    // fire into a disposed instance.
    for (const event of Object.keys(handlers)) chart?.off(event)
    chart?.dispose()
    chart = undefined
  })

  return { render }
}
