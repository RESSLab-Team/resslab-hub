import DoubleChart from '@/components/commons/charts/DoubleChart.vue'
import { NAME } from '@/plugins/echarts-theme'
import { mount } from '@vue/test-utils'
import type { EChartsOption, LegendComponentOption, TitleComponentOption } from 'echarts'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// A local i18n instance: the real plugin reads localStorage at import time.
vi.mock('@/plugins/i18n', async () => {
  const { createI18n } = await import('vue-i18n')
  const messages = { en: { test: { connection_type: 'Connection type', beam: 'Beam' } } }
  return { default: createI18n({ legacy: false, locale: 'en', messages }) }
})

// DoubleChart mounts ECharts by hand through useEChart. Keep the option getter
// it gets, the test is about that option, not about what ECharts draws.
const captured = vi.hoisted(() => ({ option: undefined as undefined | (() => unknown) }))
vi.mock('@/composables/useEChart', () => ({
  useEChart: (_el: unknown, initial: () => unknown) => {
    captured.option = initial
    return { render: () => undefined, getInstance: () => undefined }
  }
}))

// jsdom has no canvas: give the text a width that grows with its length.
vi.mock('@/components/commons/charts/utils', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/components/commons/charts/utils')>()),
  measureTextWidth: (text: string) => text.length * 7
}))

const counts = [
  { names: ['A', 'WUF-B'], value: 3 },
  { names: ['A', 'RBS'], value: 2 },
  { names: ['B', 'RBS'], value: 1 }
]

describe('DoubleChart header', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'ResizeObserver',
      class {
        observe() {}
        disconnect() {}
      }
    )
  })
  afterEach(() => vi.unstubAllGlobals())

  it('shows the legend title in muted ink, with room before the first item', () => {
    mount(DoubleChart, {
      props: {
        fields: ['beam', 'connection_type'],
        labelPrefix: 'test.',
        counts,
        allCounts: counts
      }
    })
    const option = captured.option?.() as EChartsOption
    const title = option.title as TitleComponentOption
    const legend = option.legend as LegendComponentOption
    expect(title.text).toBe('Connection type')
    expect(title.textStyle?.color).toBe(NAME)
    // The legend starts after the title text plus a gap of at least 20 px.
    const titleWidth = 'Connection type'.length * 7
    expect((legend.left as number) - (title.left as number)).toBeGreaterThanOrEqual(titleWidth + 20)
  })
})
