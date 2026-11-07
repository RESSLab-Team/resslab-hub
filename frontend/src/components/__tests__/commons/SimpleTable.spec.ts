import SimpleTable from '@/components/commons/SimpleTable.vue'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createI18n } from 'vue-i18n'
import { createVuetify } from 'vuetify'

// A local instance rather than `@/plugins/i18n`: the plugin reads localStorage at
// import time, which the test environment does not provide. `vi.hoisted` because
// `vi.mock` runs before the imports, and the component imports the plugin.
const i18n = vi.hoisted(() => ({ value: null as unknown as ReturnType<typeof createI18n> }))
vi.mock('@/plugins/i18n', async () => {
  const { createI18n } = await import('vue-i18n')
  const { default: en } = await import('@/locales/en.json')
  i18n.value = createI18n({ legacy: false, locale: 'en', messages: { en } })
  return { default: i18n.value }
})
vi.mock('vue-router', () => ({ useRoute: () => ({ fullPath: '/', query: {} }) }))

const items = Array.from({ length: 8 }, (_, i) => ({ id: `S${i + 1}`, name: `Specimen ${i + 1}` }))

function mountTable() {
  return mount(SimpleTable, {
    props: {
      items,
      columns: [{ value: 'name', type: 'text' as const, title: 'Name' }],
      totalCount: items.length,
      totalFilteredCount: items.length
    },
    global: {
      plugins: [i18n.value, createVuetify()],
      stubs: { 'v-menu': true, 'v-icon': true, 'v-dialog': true, CheckboxDialog: true }
    }
  })
}

describe('SimpleTable select all', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    // jsdom has no matchMedia; the table reads it to pick the page size.
    window.matchMedia = vi.fn().mockReturnValue({ matches: false }) as never
  })

  it('selects the whole page, then clears it on a second click', async () => {
    const wrapper = mountTable()
    const header = wrapper.find('.stbl-head-titles .stbl-check')
    const rowChecks = () =>
      wrapper.findAll('tbody .stbl-check').map((c) => (c.element as HTMLInputElement).checked)
    const download = () => wrapper.find('.dash-pager-actions button')

    await header.trigger('change')
    expect(rowChecks()).toHaveLength(8)
    expect(rowChecks().every(Boolean)).toBe(true)
    expect((header.element as HTMLInputElement).checked).toBe(true)
    expect(download().text()).toContain('8/8')
    expect(download().attributes('disabled')).toBeUndefined()

    // #327: the second click used to do nothing.
    await header.trigger('change')
    expect(rowChecks().some(Boolean)).toBe(false)
    expect(download().attributes('disabled')).toBeDefined()
  })

  it('fills a half selected page, then clears it', async () => {
    const wrapper = mountTable()
    const header = wrapper.find('.stbl-head-titles .stbl-check')
    const rowChecks = () =>
      wrapper.findAll('tbody .stbl-check').map((c) => (c.element as HTMLInputElement).checked)

    await wrapper.findAll('tbody .stbl-check')[0].trigger('change')
    expect((header.element as HTMLInputElement).indeterminate).toBe(true)

    await header.trigger('change')
    expect(rowChecks().every(Boolean)).toBe(true)

    await header.trigger('change')
    expect(rowChecks().some(Boolean)).toBe(false)
  })
})

describe('SimpleTable keyboard and labels', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.matchMedia = vi.fn().mockReturnValue({ matches: false }) as never
  })

  it('opens a row with Enter or Space, like a click', async () => {
    const wrapper = mountTable()
    const row = wrapper.findAll('tbody tr.stbl-row')[1]
    expect(row.attributes('tabindex')).toBe('0')

    await row.trigger('keydown', { key: 'Enter' })
    await row.trigger('keydown', { key: ' ' })
    expect(wrapper.emitted('click:row')).toEqual([[items[1]], [items[1]]])
  })

  it('does not open the row when Space ticks its checkbox', async () => {
    const wrapper = mountTable()
    await wrapper.find('tbody .stbl-check').trigger('keydown', { key: ' ' })
    expect(wrapper.emitted('click:row')).toBeUndefined()
  })

  it('labels the checkboxes and the pager buttons', () => {
    const wrapper = mountTable()
    expect(wrapper.find('.stbl-head-titles .stbl-check').attributes('aria-label')).toBe(
      'Select all'
    )
    expect(wrapper.find('tbody .stbl-check').attributes('aria-label')).toBe('Select S1')
    const pager = wrapper.findAll('.pager-btn')
    expect(pager[0].attributes('aria-label')).toBe('Previous')
    expect(pager[pager.length - 1].attributes('aria-label')).toBe('Next')
  })
})
