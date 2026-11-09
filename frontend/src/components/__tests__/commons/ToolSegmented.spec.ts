import ToolSegmented from '@/components/commons/tools/ToolSegmented.vue'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

const items = [
  { value: 'a', text: 'A' },
  { value: 'b', text: 'B' },
  { value: 'c', text: 'C' }
]

describe('ToolSegmented', () => {
  it('is a labelled radio group with one segment in the tab order', () => {
    const wrapper = mount(ToolSegmented, { props: { modelValue: 'b', items, label: 'Steel type' } })
    const group = wrapper.find('.tseg')
    expect(group.attributes('role')).toBe('radiogroup')
    expect(group.attributes('aria-label')).toBe('Steel type')
    const radios = wrapper.findAll('button')
    expect(radios.map((radio) => radio.attributes('role'))).toEqual(['radio', 'radio', 'radio'])
    expect(radios.map((radio) => radio.attributes('aria-checked'))).toEqual([
      'false',
      'true',
      'false'
    ])
    expect(radios.map((radio) => radio.attributes('tabindex'))).toEqual(['-1', '0', '-1'])
  })

  it('puts the first segment in the tab order when nothing is checked', () => {
    const wrapper = mount(ToolSegmented, { props: { modelValue: 'none', items } })
    expect(wrapper.findAll('button').map((radio) => radio.attributes('tabindex'))).toEqual([
      '0',
      '-1',
      '-1'
    ])
  })

  it('moves the choice and the focus with the arrow keys, wrapping at the ends', async () => {
    const wrapper = mount(ToolSegmented, {
      attachTo: document.body,
      props: { modelValue: 'c', items }
    })
    const radios = wrapper.findAll('button')

    await radios[2].trigger('keydown', { key: 'ArrowRight' })
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['a'])
    await wrapper.setProps({ modelValue: 'a' })
    expect(document.activeElement).toBe(radios[0].element)

    await radios[0].trigger('keydown', { key: 'ArrowLeft' })
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['c'])

    await radios[0].trigger('keydown', { key: 'Tab' })
    expect(wrapper.emitted('update:modelValue')).toHaveLength(2)
    wrapper.unmount()
  })
})
