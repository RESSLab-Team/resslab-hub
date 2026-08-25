import FilterInput from '@/components/commons/FilterInput.vue'
import en from '@/locales/en.json'
import type { DictColumn, DictType } from '@/stores/dictionary'
import type { Value } from '@/utils/common'
import type { FilterDescriptor } from '@/utils/filterProfile'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { createI18n } from 'vue-i18n'

// A local instance rather than `@/plugins/i18n`: the plugin reads localStorage at
// import time, which the test environment does not provide.
const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })

function column(name: string, type: DictType): DictColumn {
  return { name, description: name, symbol: '-', unit: '-', type, example: '', nullable: true }
}

const categorical: FilterDescriptor = {
  key: 'connection_type',
  column: column('connection_type', 'String'),
  kind: 'categorical',
  distinct: 2,
  nonNull: 8,
  missing: 2,
  options: [
    { value: 'RBS', count: 5 },
    { value: 'WUF-W', count: 3 }
  ]
}

const numeric: FilterDescriptor = {
  key: 'd_b',
  column: column('d_b', 'Numeric'),
  kind: 'numeric',
  distinct: 4,
  nonNull: 4,
  missing: 0,
  min: 0,
  max: 100,
  binEdges: [0, 50, 100],
  bins: [
    [0, 3, 0, 50],
    [1, 1, 50, 100]
  ]
}

/** Stand-in for the brush that records the props it was handed. */
const DistributionBrushStub = {
  props: ['fields', 'modelValue', 'min', 'max'],
  template: '<div class="brush-stub" :data-fields="fields" />'
}

function mountInput(
  filter: FilterDescriptor,
  props: { value?: Value; fields?: 'sides' | 'below'; meta?: boolean } = {}
) {
  return mount(FilterInput, {
    props: { filter, ...props },
    global: {
      plugins: [i18n],
      stubs: {
        VIcon: true,
        VTextField: true,
        VChart: true,
        DistributionBrush: DistributionBrushStub
      }
    }
  })
}

function emitted(wrapper: ReturnType<typeof mountInput>): (Value | undefined)[] {
  return (wrapper.emitted('update') ?? []).map((args) => (args as [Value | undefined])[0])
}

describe('FilterInput', () => {
  it('emits the rail grammar for a value set: exact match, then an array', async () => {
    const wrapper = mountInput(categorical)
    const boxes = wrapper.findAll('input[type="checkbox"]')
    await boxes[0].setValue(true)
    expect(emitted(wrapper)).toEqual(['=RBS'])
    await wrapper.setProps({ value: '=RBS' })
    await boxes[1].setValue(true)
    expect(emitted(wrapper)).toEqual(['=RBS', ['RBS', 'WUF-W']])
  })

  it('shows the distinct/missing footnote by default and hides it on request', () => {
    expect(mountInput(categorical).find('.afr-meta').text()).toContain('2')
    expect(mountInput(categorical, { meta: false }).find('.afr-meta').exists()).toBe(false)
  })

  it('hands the field layout to the numeric brush', () => {
    expect(mountInput(numeric).find('.brush-stub').attributes('data-fields')).toBe('sides')
    expect(
      mountInput(numeric, { fields: 'below' }).find('.brush-stub').attributes('data-fields')
    ).toBe('below')
  })
})
