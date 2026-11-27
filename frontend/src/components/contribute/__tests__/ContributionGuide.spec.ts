import ContributionGuide from '@/components/contribute/ContributionGuide.vue'
import en from '@/locales/en.json'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createI18n } from 'vue-i18n'

// The README fetch: no guide uploaded, the rail still shows the layout.
vi.mock('@/plugins/axios', () => ({
  baseUrl: '/api',
  axiosInstance: { get: vi.fn(async () => Promise.reject(new Error('404'))) }
}))

// A local instance rather than `@/plugins/i18n`: the plugin reads localStorage
// at import time.
const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })

function mountGuide() {
  return mount(ContributionGuide, {
    props: { database: 'braces', docked: true },
    global: { plugins: [i18n], stubs: { VIcon: true } }
  })
}

describe('ContributionGuide, AI agent block', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('shows a prompt that points to the agent guide of the database', async () => {
    const wrapper = mountGuide()
    await flushPromises()
    const block = wrapper.find('.agent')
    expect(block.text()).toContain('Format your data with an AI agent')
    expect(block.find('pre').text()).toContain(`${window.location.origin}/api/agent/guide/braces`)
    expect(block.find('a').attributes('href')).toBe(
      `${window.location.origin}/api/agent/guide/braces`
    )
  })

  it('copies the prompt', async () => {
    const writeText = vi.fn(async () => undefined)
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    const wrapper = mountGuide()
    await flushPromises()
    await wrapper.find('.agent button').trigger('click')
    await flushPromises()
    expect(writeText).toHaveBeenCalledWith(wrapper.find('.agent pre').text())
    expect(wrapper.find('.agent button').text()).toContain('Copied')
  })
})
