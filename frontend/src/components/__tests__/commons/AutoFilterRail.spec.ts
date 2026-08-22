import AutoFilterRail from '@/components/commons/AutoFilterRail.vue'
import type { FilterGroup, LabeledFilter } from '@/composables/useAutoFilters'
import en from '@/locales/en.json'
import type { DictColumn } from '@/stores/dictionary'
import type { Searches } from '@/utils/common'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
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
