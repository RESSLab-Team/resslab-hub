import DataLegend from '@/components/curation/DataLegend.vue'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

describe('DataLegend', () => {
  it('draws one swatch per item, styled by its kind', () => {
    const wrapper = mount(DataLegend, {
      props: {
        items: [
          { kind: 'submitted', label: 'Submitted' },
          { kind: 'existing', label: 'Existing' }
        ]
      }
    })
    const swatches = wrapper.findAll('.sw')
    expect(swatches).toHaveLength(2)
    expect(swatches[0].classes()).toContain('submitted')
    expect(swatches[1].classes()).toContain('existing')
    expect(wrapper.text()).toContain('Submitted')
    expect(wrapper.text()).toContain('Existing')
  })
})
