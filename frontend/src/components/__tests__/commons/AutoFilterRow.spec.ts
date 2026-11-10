import AutoFilterRow from '@/components/commons/AutoFilterRow.vue'
import type { LabeledFilter } from '@/composables/useAutoFilters'
import en from '@/locales/en.json'
import type { DictColumn, DictType } from '@/stores/dictionary'
import type { Value } from '@/utils/common'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { createI18n } from 'vue-i18n'

// A local instance rather than `@/plugins/i18n`: the plugin reads localStorage at
// import time, which the test environment does not provide.
const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })

function column(name: string, type: DictType): DictColumn {
  return { name, description: name, symbol: '-', unit: '-', type, example: '', nullable: true }
}

const categorical: LabeledFilter = {
  key: 'connection_type',
  column: column('connection_type', 'String'),
  kind: 'categorical',
  label: 'Connection type',
  distinct: 3,
  nonNull: 10,
  missing: 2,
  notReported: 0,
  notApplicable: 2,
  options: [
    { value: 'RBS', count: 5 },
    { value: 'WUF-W', count: 3 },
    { value: 'NA', count: 2 }
  ]
}

function mountRow(filter: LabeledFilter, value?: Value, open = true) {
  return mount(AutoFilterRow, {
    props: { filter, value, open },
    global: {
      plugins: [i18n],
      stubs: { VIcon: true, TextSubscript: true, VTextField: true, VChart: true }
    }
  })
}

/** The values emitted to `changeSearches`, in order. */
function emitted(wrapper: ReturnType<typeof mountRow>): (Value | undefined)[] {
  return (wrapper.emitted('update') ?? []).map((args) => (args as [Value | undefined])[0])
}

describe('AutoFilterRow: value-set filters', () => {
  it('emits a single selection as an exact match, not a substring', async () => {
    const wrapper = mountRow(categorical)
    await wrapper.findAll('input[type="checkbox"]')[0].setValue(true)
    // `RBS` alone would also match `RBS-b`; `=RBS` is the exact-match operator.
    expect(emitted(wrapper)).toEqual(['=RBS'])
  })

  it('emits two or more selections as an array (the DSL value set)', async () => {
    const wrapper = mountRow(categorical, '=RBS')
    await wrapper.findAll('input[type="checkbox"]')[1].setValue(true)
    expect(emitted(wrapper)).toEqual([['RBS', 'WUF-W']])
  })

  it('clears the filter when the last box is unchecked', async () => {
    const wrapper = mountRow(categorical, '=RBS')
    await wrapper.findAll('input[type="checkbox"]')[0].setValue(false)
    expect(emitted(wrapper)).toEqual([undefined])
  })

  it('drops one value from a set without losing the others', async () => {
    const wrapper = mountRow(categorical, ['RBS', 'WUF-W'])
    await wrapper.findAll('input[type="checkbox"]')[1].setValue(false)
    expect(emitted(wrapper)).toEqual(['=RBS'])
  })

  it('reflects the bare value a chart click writes as a checked box', () => {
    const wrapper = mountRow(categorical, 'RBS')
    const boxes = wrapper.findAll('input[type="checkbox"]')
    expect((boxes[0].element as HTMLInputElement).checked).toBe(true)
    expect((boxes[1].element as HTMLInputElement).checked).toBe(false)
  })

  it('offers the missing bucket, which matches nulls through the NA sentinel', async () => {
    const wrapper = mountRow(categorical)
    await wrapper.findAll('input[type="checkbox"]')[2].setValue(true)
    expect(emitted(wrapper)).toEqual(['=NA'])
  })
})

describe('AutoFilterRow: booleans', () => {
  const boolean: LabeledFilter = {
    key: 'slab',
    column: column('slab', 'Boolean'),
    kind: 'boolean',
    label: 'Slab',
    distinct: 2,
    nonNull: 8,
    missing: 0,
    notReported: 0,
    notApplicable: 0,
    options: [
      { value: 'True', count: 5 },
      { value: 'False', count: 3 }
    ]
  }

  it('emits the formatted boolean the query engine compares against', async () => {
    const wrapper = mountRow(boolean)
    await wrapper.findAll('input[type="checkbox"]')[0].setValue(true)
    expect(emitted(wrapper)).toEqual(['=True'])
  })

  it('checks the box for a legacy boolean value regardless of case', () => {
    const wrapper = mountRow(boolean, true)
    expect((wrapper.findAll('input[type="checkbox"]')[0].element as HTMLInputElement).checked).toBe(
      true
    )
  })
})

describe('AutoFilterRow: text', () => {
  const text: LabeledFilter = {
    key: 'reference',
    column: column('reference', 'String'),
    kind: 'text',
    label: 'Reference',
    distinct: 40,
    nonNull: 50,
    missing: 0,
    notReported: 0,
    notApplicable: 0,
    options: [{ value: 'Demo et al.', count: 4 }]
  }

  it('emits the raw string, which the engine matches as a substring', async () => {
    const wrapper = mountRow(text)
    await wrapper.get('input.afr-text').setValue('  Demo  ')
    expect(emitted(wrapper)).toEqual(['Demo'])
  })

  it('clears the filter on an empty search', async () => {
    const wrapper = mountRow(text, 'Demo')
    await wrapper.get('input.afr-text').setValue('')
    expect(emitted(wrapper)).toEqual([undefined])
  })

  it('picks the value of a recurring-value shortcut', async () => {
    const wrapper = mountRow(text)
    await wrapper.get('button.afr-option').trigger('click')
    expect(emitted(wrapper)).toEqual(['Demo et al.'])
  })
})

describe('AutoFilterRow: collapsed row', () => {
  it('mounts no body until it is opened', () => {
    const closed = mountRow(categorical, undefined, false)
    expect(closed.find('.afr-body').exists()).toBe(false)
    expect(mountRow(categorical).find('.afr-body').exists()).toBe(true)
  })

  it('summarises the active value, hiding the DSL operator', () => {
    expect(mountRow(categorical, '=RBS', false).get('.afr-summary').text()).toBe('RBS')
    expect(mountRow(categorical, ['RBS', 'WUF-W'], false).get('.afr-summary').text()).toBe(
      '2 selected'
    )
  })

  it('renders a range as bounds', () => {
    const numeric: LabeledFilter = {
      key: 'kl_r',
      column: column('kl_r', 'DecimalFloat'),
      kind: 'numeric',
      label: 'Slenderness',
      distinct: 20,
      nonNull: 20,
      missing: 0,
      notReported: 0,
      notApplicable: 0,
      min: 0,
      max: 100
    }
    expect(mountRow(numeric, '20<<80', false).get('.afr-summary').text()).toBe('20 – 80')
  })

  it('clears the filter from the collapsed row', async () => {
    const wrapper = mountRow(categorical, '=RBS', false)
    await wrapper.get('.afr-clear').trigger('click')
    expect(emitted(wrapper)).toEqual([undefined])
  })

  it('has no clear button when nothing is filtered', () => {
    expect(mountRow(categorical, undefined, false).find('.afr-clear').exists()).toBe(false)
  })
})
