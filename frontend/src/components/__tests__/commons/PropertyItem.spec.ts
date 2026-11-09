import PropertyItem from '@/components/commons/PropertyItem.vue'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

describe('PropertyItem', () => {
  it('renders a dictionary symbol with a real subscript', () => {
    const wrapper = mount(PropertyItem, { props: { name: 'd<sub>pz</sub>' } })
    expect(wrapper.find('.prop-name sub').text()).toBe('pz')
    expect(wrapper.find('.prop-name').text()).toBe('dpz')
  })

  it('renders a plain label as text', () => {
    const wrapper = mount(PropertyItem, { props: { name: 'Beam section' } })
    expect(wrapper.find('.prop-name').text()).toBe('Beam section')
    expect(wrapper.find('.prop-name sub').exists()).toBe(false)
  })
})
