import DistributionBrush from '@/components/commons/sliders/DistributionBrush.vue'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

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
