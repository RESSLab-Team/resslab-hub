import AutoFilterRail from '@/components/commons/AutoFilterRail.vue'
import type { FilterGroup, LabeledFilter } from '@/composables/useAutoFilters'
import en from '@/locales/en.json'
import type { DictColumn } from '@/stores/dictionary'
import type { Searches } from '@/utils/common'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { nextTick, reactive } from 'vue'
import { createI18n } from 'vue-i18n'

// A local instance rather than `@/plugins/i18n`: the plugin reads localStorage at
// import time, which the test environment does not provide.
const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })

function column(name: string, description = name): DictColumn {
  return { name, description, symbol: '-', unit: '-', type: 'String', example: '', nullable: true }
}

function filter(key: string, label: string, description = key): LabeledFilter {
  return {
    key,
    column: column(key, description),
    kind: 'categorical',
    label,
    distinct: 2,
    nonNull: 10,
    missing: 0,
    options: [{ value: 'a', count: 10 }]
  }
}

const GROUPS: FilterGroup[] = [
  {
    id: 'experimental_program_details',
    label: 'Experimental program details',
    filters: [filter('id', 'Specimen'), filter('date', 'Year')]
  },
  {
    id: 'section_properties',
    label: 'Section properties',
    filters: [filter('d_br', 'Brace depth'), filter('area', 'Area', 'cross section area')]
  },
  {
    id: 'material_properties',
    label: 'Material properties',
    filters: [filter('steel', 'Steel grade')]
  }
]

function mountRail(searches: Searches = {}) {
  return mount(AutoFilterRail, {
    props: { groups: GROUPS, searches },
    global: { plugins: [i18n], stubs: { VIcon: true, AutoFilterRow: true } }
  })
}

/** Labels of the group headers currently rendered, in order. */
function headers(wrapper: ReturnType<typeof mountRail>): string[] {
  return wrapper.findAll('.afr-group-label').map((node) => node.text())
}

/** Labels of the groups whose body is mounted. */
function expanded(wrapper: ReturnType<typeof mountRail>): string[] {
  return wrapper
    .findAll('.afr-group')
    .filter((group) => group.find('.afr-group-body').exists())
    .map((group) => group.get('.afr-group-label').text())
}

describe('AutoFilterRail: default state', () => {
  it('opens identification and leaves the rest collapsed', () => {
    const wrapper = mountRail()
    expect(headers(wrapper)).toEqual([
      'Experimental program details',
      'Section properties',
      'Material properties'
    ])
    expect(expanded(wrapper)).toEqual(['Experimental program details'])
  })

  it('mounts no rows for a collapsed group', () => {
    // The point of grouping: a 150-filter rail must not mount 150 rows to open.
    expect(mountRail().findAll('auto-filter-row-stub')).toHaveLength(2)
  })

  it('also opens a group that already carries a filter', () => {
    // A shared or bookmarked URL has to show what it is filtering on.
    expect(expanded(mountRail({ steel: '=S355' }))).toEqual([
      'Experimental program details',
      'Material properties'
    ])
  })

  it('counts the filters in each group, and the active ones', () => {
    const wrapper = mountRail({ steel: '=S355' })
    expect(wrapper.findAll('.afr-group-count').map((node) => node.text())).toEqual(['2', '2', '1'])
    expect(wrapper.findAll('.afr-group-active').map((node) => node.text())).toEqual(['1'])
  })
})

describe('AutoFilterRail: toggling', () => {
  it('opens a group on click and closes it again', async () => {
    const wrapper = mountRail()
    await wrapper.findAll('.afr-group-head')[1].trigger('click')
    expect(expanded(wrapper)).toEqual(['Experimental program details', 'Section properties'])
    await wrapper.findAll('.afr-group-head')[1].trigger('click')
    expect(expanded(wrapper)).toEqual(['Experimental program details'])
  })
})

describe('AutoFilterRail: expand all, collapse all', () => {
  it('opens every group, then closes every group', async () => {
    const wrapper = mountRail()
    const button = wrapper.get('button.expand')
    expect(button.text()).toBe('Expand all')
    await button.trigger('click')
    expect(expanded(wrapper)).toEqual(headers(wrapper))
    expect(button.text()).toBe('Collapse all')
    await button.trigger('click')
    expect(expanded(wrapper)).toEqual([])
    expect(button.text()).toBe('Expand all')
  })

  it('says collapse as soon as the reader has opened the last group by hand', async () => {
    const wrapper = mountRail()
    await wrapper.findAll('.afr-group-head')[1].trigger('click')
    expect(wrapper.get('button.expand').text()).toBe('Expand all')
    await wrapper.findAll('.afr-group-head')[2].trigger('click')
    expect(wrapper.get('button.expand').text()).toBe('Collapse all')
  })

  it('touches the groups only, not the rows inside', async () => {
    const wrapper = mountRail()
    await wrapper.get('button.expand').trigger('click')
    const rows = wrapper.findAll('auto-filter-row-stub')
    expect(rows).toHaveLength(5)
    expect(rows.every((row) => row.attributes('open') === 'false')).toBe(true)
  })

  it('is hidden while searching, and the hits stay visible after a collapse', async () => {
    const wrapper = mountRail()
    await wrapper.get('button.expand').trigger('click')
    await wrapper.get('button.expand').trigger('click')
    await wrapper.get('.afr-search input').setValue('brace depth')
    expect(wrapper.find('button.expand').exists()).toBe(false)
    expect(expanded(wrapper)).toEqual(['Section properties'])
  })

  it('is not offered before the filters exist', () => {
    const wrapper = mount(AutoFilterRail, {
      props: { groups: [], searches: {} },
      global: { plugins: [i18n], stubs: { VIcon: true, AutoFilterRow: true } }
    })
    expect(wrapper.find('button.expand').exists()).toBe(false)
  })
})

describe('AutoFilterRail: a filter that becomes active after mount', () => {
  function rowOpen(wrapper: ReturnType<typeof mountRail>, index: number): string | undefined {
    return wrapper.findAll('auto-filter-row-stub')[index].attributes('open')
  }

  it('opens its group and its row', async () => {
    const wrapper = mountRail()
    expect(expanded(wrapper)).toEqual(['Experimental program details'])
    await wrapper.setProps({ searches: { steel: '=S355' } })
    expect(expanded(wrapper)).toEqual(['Experimental program details', 'Material properties'])
    expect(rowOpen(wrapper, 2)).toBe('true')
  })

  it('reacts to a key added in place, the way the dashboard writes it', async () => {
    const searches = reactive<Searches>({})
    const wrapper = mountRail(searches)
    searches.steel = '=S355'
    await nextTick()
    expect(expanded(wrapper)).toEqual(['Experimental program details', 'Material properties'])
  })

  it('never closes anything when a filter goes away', async () => {
    const wrapper = mountRail({ steel: '=S355' })
    await wrapper.setProps({ searches: {} })
    expect(expanded(wrapper)).toEqual(['Experimental program details', 'Material properties'])
  })

  it('leaves a group alone if the reader closed it and its value only changes', async () => {
    const wrapper = mountRail({ steel: '=S355' })
    await wrapper.findAll('.afr-group-head')[2].trigger('click')
    await wrapper.setProps({ searches: { steel: '=S460' } })
    expect(expanded(wrapper)).toEqual(['Experimental program details'])
  })

  it('ignores a key that has no filter, like a ratio brushed on a chart', async () => {
    const wrapper = mountRail()
    await wrapper.setProps({ searches: { 'a/b': '0<<1' } })
    expect(expanded(wrapper)).toEqual(['Experimental program details'])
  })
})

describe('AutoFilterRail: search', () => {
  it('keeps only the groups holding a match, and opens them', async () => {
    const wrapper = mountRail()
    await wrapper.get('.afr-search input').setValue('brace depth')
    expect(headers(wrapper)).toEqual(['Section properties'])
    expect(expanded(wrapper)).toEqual(['Section properties'])
  })

  it('finds a variable by its dictionary description, not just its label', async () => {
    const wrapper = mountRail()
    await wrapper.get('.afr-search input').setValue('cross section')
    expect(wrapper.findAll('auto-filter-row-stub')).toHaveLength(1)
  })

  it('reports when nothing matches', async () => {
    const wrapper = mountRail()
    await wrapper.get('.afr-search input').setValue('nothing at all')
    // Compared against the literal, not against `en.commons.*`: createI18n
    // compiles the messages object in place, so its strings become functions.
    expect(wrapper.find('.afr-empty').text()).toBe('No variable matches this search.')
  })
})

describe('AutoFilterRail: reset', () => {
  it('clears every active filter, across groups', async () => {
    const wrapper = mountRail({ steel: '=S355', date: '2020' })
    await wrapper.get('button.reset').trigger('click')
    expect(wrapper.emitted('change:searches')).toEqual([
      ['date', undefined],
      ['steel', undefined]
    ])
  })
})

describe('AutoFilterRail: filters arriving after mount', () => {
  // The overlay is mounted with the dashboard, long before the dataset has
  // loaded, so the seeding has to survive an initially empty group list.
  it('opens the active group once the filters finally arrive', async () => {
    const wrapper = mount(AutoFilterRail, {
      props: { groups: [], searches: { steel: '=S355' } },
      global: { plugins: [i18n], stubs: { VIcon: true, AutoFilterRow: true } }
    })
    expect(wrapper.findAll('.afr-group')).toHaveLength(0)
    await wrapper.setProps({ groups: GROUPS })
    expect(expanded(wrapper as ReturnType<typeof mountRail>)).toEqual([
      'Experimental program details',
      'Material properties'
    ])
  })
})
