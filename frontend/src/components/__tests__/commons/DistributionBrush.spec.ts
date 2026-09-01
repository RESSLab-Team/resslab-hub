import DistributionBrush from '@/components/commons/sliders/DistributionBrush.vue'
import { blendHex } from '@/utils/palette'
import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

// The component imports VChart directly (script setup resolves it at compile
// time), so `global.stubs` can't reach it, mock the module instead. The stub
// keeps the option, which is what the stacking tests below read.
vi.mock('vue-echarts', () => ({
  default: { name: 'VChartStub', props: ['option'], template: '<div class="v-chart-stub" />' }
}))

/** The number fields, stubbed to plain inputs so their order and values are checkable. */
const VTextFieldStub = {
  props: ['modelValue'],
  template: '<input type="number" :value="modelValue" />'
}

function mountBrush(fields?: 'sides' | 'below') {
  return mount(DistributionBrush, {
    props: { min: 0, max: 100, modelValue: [10, 90], fields },
    global: { stubs: { VChart: true, VTextField: VTextFieldStub } }
  })
}

describe('DistributionBrush field layout', () => {
  it('flanks the chart with the bounds by default', () => {
    const wrapper = mountBrush()
    expect(wrapper.classes()).not.toContain('dist-brush--stacked')
    const children = wrapper.element.children
    expect(children[0].classList.contains('dist-brush__min')).toBe(true)
    expect(children[1].classList.contains('dist-brush__chart')).toBe(true)
    expect(children[2].classList.contains('dist-brush__max')).toBe(true)
  })

  it('keeps the same DOM and marks the root when the bounds go below the chart', () => {
    const wrapper = mountBrush('below')
    expect(wrapper.classes()).toContain('dist-brush--stacked')
    const inputs = wrapper.findAll('input[type="number"]')
    expect(inputs.map((input) => (input.element as HTMLInputElement).value)).toEqual(['10', '90'])
  })
})

/** Three bands, the way DoubleChart hands them over: raw counts, bottom first. */
const bands = [
  { color: '#0072B2', data: [[10, 30] as [number, number], [90, 10] as [number, number]] },
  { color: '#E69F00', data: [[10, 7] as [number, number], [90, 4] as [number, number]] },
  { color: '#009E73', data: [[10, 3] as [number, number], [90, 1] as [number, number]] }
]

function optionOf(props: Record<string, unknown>) {
  const wrapper = mount(DistributionBrush, {
    props: { min: 0, max: 100, series: bands, ...props },
    global: { stubs: { VTextField: VTextFieldStub } }
  })
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return wrapper.findComponent({ name: 'VChartStub' }).props('option') as any
}

describe('DistributionBrush stacking', () => {
  it('stacks the bands like the chart above, top band drawn first', () => {
    const series = optionOf({ modelValue: [0, 100] }).series
    expect(series).toHaveLength(3)
    expect(series.map((serie: { data: { value: number[] }[] }) => serie.data[0].value)).toEqual([
      [10, 40], // green on top of amber on top of blue
      [10, 37],
      [10, 30] // blue is the bottom band, so its own count
    ])
    // ECharts' own stack is a no-op on a value x axis, so it must not be set.
    expect(series.some((serie: { stack?: string }) => serie.stack)).toBe(false)
  })

  it('pins the y axis to the stacked total', () => {
    expect(optionOf({ modelValue: [0, 100] }).yAxis.max).toBe(40)
  })

  it('paints every band opaque, muting the slices outside the window', () => {
    const series = optionOf({ modelValue: [0, 50] }).series
    const colorAt = (index: number, point: number) => series[index].data[point].itemStyle.color
    expect(colorAt(2, 0)).toBe('#0072B2') // x = 10, inside the window
    expect(colorAt(2, 1)).toBe(blendHex('#0072B2', '#FFFFFF', 0.72)) // x = 90, outside
    expect(series[2].data[0].itemStyle.opacity).toBeUndefined()
  })

  it('fogs a line brush from its own series, above the bands', () => {
    const series = optionOf({ modelValue: [20, 80], type: 'line' }).series
    expect(series).toHaveLength(4)
    expect(series[0].areaStyle).toEqual({ color: blendHex('#009E73', '#FFFFFF', 0.3), opacity: 1 })
    expect(series[3].data).toEqual([])
    expect(series[3].markArea.data).toHaveLength(2) // left and right of the window
  })
})
