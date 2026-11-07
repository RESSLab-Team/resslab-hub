import ExperimentCards from '@/components/contribute/ExperimentCards.vue'
import { useContributionStore } from '@/stores/contribution'
import { useDictionaryStore, type DictColumn } from '@/stores/dictionary'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { describe, expect, it, vi } from 'vitest'
import { createI18n } from 'vue-i18n'
import { createVuetify } from 'vuetify'

// A local i18n instance: the real plugin reads localStorage at import time.
const i18n = vi.hoisted(() => ({ value: null as unknown as ReturnType<typeof createI18n> }))
vi.mock('@/plugins/i18n', async () => {
  const { createI18n } = await import('vue-i18n')
  const { default: en } = await import('@/locales/en.json')
  i18n.value = createI18n({ legacy: false, locale: 'en', messages: { en } })
  return { default: i18n.value }
})

function column(name: string, description = ''): DictColumn {
  return { name, description, symbol: '', unit: '-', type: 'String', example: '', nullable: true }
}

describe('ExperimentCards field names', () => {
  it('shows the raw CSV header in monospace, where the contributor types it', async () => {
    // jsdom has no layout: opening a card scrolls it into view.
    Element.prototype.scrollIntoView = vi.fn()
    setActivePinia(createPinia())
    const dictionary = useDictionaryStore()
    dictionary.columns = { connections: [column('id'), column('d_pz', 'Panel zone depth')] }
    dictionary.state = 'ready'
    const store = useContributionStore()
    store.selectDatabase('connections')
    const uid = store.addRow()

    const wrapper = mount(ExperimentCards, {
      attachTo: document.body,
      global: { plugins: [i18n.value, createVuetify()], stubs: { 'v-icon': true } }
    })
    await (wrapper.vm as unknown as { reveal(uid: number): Promise<void> }).reveal(uid)
    await flushPromises()

    // The card headline.
    expect(wrapper.find('.headline-item .k code.col-name').text()).toBe('d_pz')

    // The field label, once its group is open.
    for (const toggle of wrapper.findAll('.field-group-toggle')) await toggle.trigger('click')
    const label = wrapper.find(`label[for="f-${uid}-d_pz"]`)
    expect(label.find('code.col-name').text()).toBe('d_pz')
    expect(label.text()).not.toContain('D pz')
    wrapper.unmount()
  })
})
