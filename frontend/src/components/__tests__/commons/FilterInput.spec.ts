import FilterInput from '@/components/commons/FilterInput.vue'
import { dashboardQueryKey } from '@/composables/dashboard'
import { filterCountsKey, type CountsFor } from '@/composables/useAutoFilters'
import en from '@/locales/en.json'
import type { DictColumn, DictType } from '@/stores/dictionary'
import type { Value } from '@/utils/common'
import { liveCounts } from '@/utils/filterCounts'
import type { FilterDescriptor } from '@/utils/filterProfile'
import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { nextTick, ref } from 'vue'
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
    ['0', 3, 0, 50],
    ['1', 1, 50, 100]
  ]
}

/** Stand-in for the brush that records the props it was handed. */
const DistributionBrushStub = {
  props: ['fields', 'modelValue', 'min', 'max', 'series'],
  template: '<div class="brush-stub" :data-fields="fields" />'
}

function mountInput(
  filter: FilterDescriptor,
  props: { value?: Value; fields?: 'sides' | 'below'; meta?: boolean } = {},
  provide: Record<symbol, unknown> = {}
) {
  return mount(FilterInput, {
    props: { filter, ...props },
    global: {
      plugins: [i18n],
      provide,
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

  describe('text shortcuts', () => {
    const text: FilterDescriptor = {
      key: 'investigator',
      column: { name: 'investigator' } as DictColumn,
      kind: 'text',
      distinct: 20,
      nonNull: 100,
      missing: 0,
      options: [
        { value: 'Fell, Kanvinde & Deierlein', count: 6 },
        { value: 'Black et al.', count: 4 }
      ]
    }

    function shortcut(wrapper: ReturnType<typeof mountInput>, index: number) {
      return wrapper.findAll('button.afr-option')[index]
    }

    it('picks the exact value, comma included', async () => {
      const wrapper = mountInput(text)
      await shortcut(wrapper, 0).trigger('click')
      expect(emitted(wrapper)).toEqual(['=Fell, Kanvinde & Deierlein'])
    })

    it('reads back as selected, and a second click clears the filter', async () => {
      const wrapper = mountInput(text, { value: '=Fell, Kanvinde & Deierlein' })
      expect(shortcut(wrapper, 0).classes()).toContain('on')
      expect(shortcut(wrapper, 0).attributes('aria-pressed')).toBe('true')
      expect(shortcut(wrapper, 1).classes()).not.toContain('on')
      await shortcut(wrapper, 0).trigger('click')
      expect(emitted(wrapper)).toEqual([undefined])
    })

    it('moves to another value on a click on that value', async () => {
      const wrapper = mountInput(text, { value: '=Fell, Kanvinde & Deierlein' })
      await shortcut(wrapper, 1).trigger('click')
      expect(emitted(wrapper)).toEqual(['=Black et al.'])
    })

    it('also lights up for a bare value, the way a chart writes it', () => {
      const wrapper = mountInput(text, { value: 'Black et al.' })
      expect(shortcut(wrapper, 1).classes()).toContain('on')
    })

    it('keeps the value in the search box, without the equals sign', () => {
      const wrapper = mountInput(text, { value: '=Black et al.' })
      expect((wrapper.get('input.afr-text').element as HTMLInputElement).value).toBe('Black et al.')
    })
  })

  describe('counts that follow the other filters', () => {
    // What the rows left by the other filters look like: no WUF-W anymore.
    const RBS_ROWS = [{ connection_type: 'RBS' }, { connection_type: 'RBS' }]

    function mountLive(filter: FilterDescriptor, query: string, props: { value?: Value } = {}) {
      const countsFor = vi.fn<CountsFor>((target) => liveCounts(RBS_ROWS, target))
      const queryRef = ref<string | undefined>(query)
      const wrapper = mountInput(filter, props, {
        [filterCountsKey as symbol]: countsFor,
        [dashboardQueryKey as symbol]: queryRef
      })
      return { wrapper, countsFor, queryRef }
    }

    function optionTexts(wrapper: ReturnType<typeof mountInput>): string[] {
      return wrapper.findAll('.afr-option-count').map((count) => count.text())
    }

    it('keeps the static counts with no provider, and no total', () => {
      const wrapper = mountInput(categorical)
      expect(optionTexts(wrapper)).toEqual(['5', '3'])
      expect(wrapper.find('.afr-option-total').exists()).toBe(false)
    })

    it('shows the live count over the total when another filter is active', () => {
      const { wrapper, countsFor } = mountLive(categorical, 'd_b:0<<10')
      expect(countsFor).toHaveBeenCalledWith(categorical, 'd_b:0<<10')
      expect(optionTexts(wrapper)).toEqual(['2 / 5', '0 / 3'])
    })

    it('mutes a value with no row left, and it can still be ticked', async () => {
      const { wrapper } = mountLive(categorical, 'd_b:0<<10')
      const options = wrapper.findAll('.afr-option')
      expect(options[0].classes()).not.toContain('zero')
      expect(options[1].classes()).toContain('zero')
      await wrapper.findAll('input[type="checkbox"]')[1].setValue(true)
      expect(emitted(wrapper)).toEqual(['=WUF-W'])
    })

    it('draws the bar from the live count, on the scale of the whole dataset', () => {
      const { wrapper } = mountLive(categorical, 'd_b:0<<10')
      const bars = wrapper.findAll('.afr-option-bar')
      expect(bars[0].attributes('style')).toContain('width: 40%')
      expect(bars[1].attributes('style')).toContain('width: 0%')
    })

    it('leaves its own clause out, so a selection can still be widened', () => {
      const { wrapper, countsFor } = mountLive(categorical, 'connection_type:=RBS;d_b:0<<10', {
        value: '=RBS'
      })
      expect(countsFor).toHaveBeenCalledWith(categorical, 'd_b:0<<10')
      expect(wrapper.find('.afr-option.on').exists()).toBe(true)
    })

    it('shows a plain count when its own filter is the only active one', () => {
      const { wrapper, countsFor } = mountLive(categorical, 'connection_type:=RBS', {
        value: '=RBS'
      })
      expect(countsFor).toHaveBeenCalledWith(categorical, undefined)
      expect(wrapper.find('.afr-option-total').exists()).toBe(false)
    })

    it('counts again only when the other filters change', async () => {
      const { countsFor, queryRef } = mountLive(categorical, 'connection_type:=RBS;d_b:0<<10')
      expect(countsFor).toHaveBeenCalledTimes(1)
      queryRef.value = 'connection_type:RBS,WUF-W;d_b:0<<10'
      await nextTick()
      expect(countsFor).toHaveBeenCalledTimes(1)
      queryRef.value = 'connection_type:RBS,WUF-W;d_b:0<<20'
      await nextTick()
      expect(countsFor).toHaveBeenCalledTimes(2)
    })

    it('feeds the live bins to the brush and keeps its static extent', () => {
      const countsFor = vi.fn<CountsFor>(() => ({
        bins: [
          ['0', '', 0, 50],
          ['1', 1, 50, 100]
        ]
      }))
      const wrapper = mountInput(
        numeric,
        {},
        {
          [filterCountsKey as symbol]: countsFor,
          [dashboardQueryKey as symbol]: ref('connection_type:=RBS')
        }
      )
      const brush = wrapper.findComponent(DistributionBrushStub)
      expect(brush.props('series')[0].data).toEqual([
        [25, 0],
        [75, 1]
      ])
      expect(brush.props('min')).toBe(0)
      expect(brush.props('max')).toBe(100)
    })
  })
})
