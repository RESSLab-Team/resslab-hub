import DashboardShell from '@/components/commons/DashboardShell.vue'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createI18n, type Composer } from 'vue-i18n'
import { createVuetify } from 'vuetify'

// Same local i18n as SimpleTable.spec.ts: the real plugin reads localStorage at import.
const i18n = vi.hoisted(() => ({ value: null as unknown as ReturnType<typeof createI18n> }))
vi.mock('@/plugins/i18n', async () => {
  const { createI18n } = await import('vue-i18n')
  const { default: en } = await import('@/locales/en.json')
  i18n.value = createI18n({ legacy: false, locale: 'en', messages: { en } })
  return { default: i18n.value }
})
vi.mock('vue-router', () => ({ useRoute: () => ({ fullPath: '/', query: {} }) }))

function mountShell(detailOpen: boolean, searches = {}) {
  return mount(DashboardShell, {
    attachTo: document.body,
    props: {
      eyebrow: 'Database',
      title: 'Braces',
      i18nPrefix: 'brace.',
      filters: [],
      filterGroups: [],
      searches,
      detailOpen
    },
    slots: { detail: '<button class="inside">Inside</button>' },
    global: {
      plugins: [i18n.value, createVuetify()],
      stubs: { 'v-icon': true, AutoFilterRail: true }
    }
  })
}

function press(key: string): void {
  window.dispatchEvent(new KeyboardEvent('keydown', { key }))
}

describe('DashboardShell drawers', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('keeps the closed drawers and their scrims out of the keyboard path', () => {
    const wrapper = mountShell(false)
    expect(wrapper.find('aside.drawer').attributes('inert')).toBeDefined()
    expect(wrapper.find('aside.filters-overlay').attributes('inert')).toBeDefined()
    const scrims = wrapper.findAll('.drawer-scrim')
    expect(scrims).toHaveLength(2)
    scrims.forEach((scrim) => {
      expect(scrim.element.tagName).toBe('BUTTON')
      expect(scrim.attributes('aria-label')).toBe('Close')
      expect(scrim.attributes('inert')).toBeDefined()
    })
    wrapper.unmount()
  })

  it('opens the detail drawer, takes the focus, closes on Escape and on the scrim', async () => {
    const opener = document.createElement('button')
    document.body.appendChild(opener)
    opener.focus()

    const wrapper = mountShell(false)
    await wrapper.setProps({ detailOpen: true })
    await new Promise((resolve) => setTimeout(resolve))
    const drawer = wrapper.find('aside.drawer')
    expect(drawer.attributes('inert')).toBeUndefined()
    expect(document.activeElement).toBe(drawer.element)

    press('Escape')
    expect(wrapper.emitted('close:detail')).toHaveLength(1)
    await wrapper.find('.drawer-scrim').trigger('click')
    expect(wrapper.emitted('close:detail')).toHaveLength(2)

    // The parent closes it: the focus goes back to what opened it.
    await wrapper.setProps({ detailOpen: false })
    expect(document.activeElement).toBe(opener)

    press('Escape')
    expect(wrapper.emitted('close:detail')).toHaveLength(2)
    wrapper.unmount()
    opener.remove()
  })

  it('makes the filter chip remove a real button', async () => {
    const wrapper = mountShell(false, { name: 'HSS' })
    const remove = wrapper.find('.fchip-x')
    expect(remove.element.tagName).toBe('BUTTON')
    await remove.trigger('click')
    expect(wrapper.emitted('change:searches')).toEqual([['name', undefined]])
    wrapper.unmount()
  })
})

describe('DashboardShell search placeholder', () => {
  function placeholder(props: Record<string, unknown> = {}): string | undefined {
    const wrapper = mount(DashboardShell, {
      props: {
        eyebrow: 'Database',
        title: 'Braces',
        i18nPrefix: 'brace.',
        filters: [],
        filterGroups: [],
        searches: {},
        ...props
      },
      global: {
        plugins: [i18n.value, createVuetify()],
        stubs: { 'v-icon': true, AutoFilterRail: true }
      }
    })
    const value = wrapper.find('input[type="search"]').attributes('placeholder')
    wrapper.unmount()
    return value
  }

  it('translates the default and keeps a given one as is', () => {
    const global = i18n.value.global as unknown as Composer
    global.setLocaleMessage('fr', { commons: { dash_search_placeholder: 'Chercher partout…' } })
    global.locale.value = 'fr'
    try {
      expect(placeholder()).toBe('Chercher partout…')
      expect(placeholder({ searchPlaceholder: 'Search ids' })).toBe('Search ids')
      // The English text passed on purpose is not swapped for the translation.
      expect(placeholder({ searchPlaceholder: 'Search all columns…' })).toBe('Search all columns…')
    } finally {
      global.locale.value = 'en'
    }
    expect(placeholder()).toBe('Search all columns…')
  })
})

describe('DashboardShell count label', () => {
  function countText(props: Record<string, unknown> = {}): string {
    const wrapper = mount(DashboardShell, {
      props: {
        eyebrow: 'Database',
        title: 'Braces',
        count: 12,
        i18nPrefix: 'brace.',
        filters: [],
        filterGroups: [],
        searches: {},
        ...props
      },
      global: {
        plugins: [i18n.value, createVuetify()],
        stubs: { 'v-icon': true, AutoFilterRail: true }
      }
    })
    const value = wrapper.find('.dash-title-count').text()
    wrapper.unmount()
    return value
  }

  it('translates the default and keeps a given one as is', () => {
    const global = i18n.value.global as unknown as Composer
    global.setLocaleMessage('fr', { commons: { dash_count_label: 'essais' } })
    global.locale.value = 'fr'
    try {
      expect(countText()).toBe('12 essais')
      // The English default passed on purpose is not swapped for the translation.
      expect(countText({ countLabel: 'tests' })).toBe('12 tests')
      expect(countText({ countLabel: 'éprouvettes' })).toBe('12 éprouvettes')
    } finally {
      global.locale.value = 'en'
    }
    expect(countText()).toBe('12 tests')
  })
})
