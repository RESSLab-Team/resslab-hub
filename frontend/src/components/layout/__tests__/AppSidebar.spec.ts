import AppSidebar from '@/components/layout/AppSidebar.vue'
import en from '@/locales/en.json'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createI18n } from 'vue-i18n'

const getFeatures = vi.fn()
const getMe = vi.fn()

vi.mock('@/plugins/axios', () => ({
  defaultApi: { getFeatures: (...args: unknown[]) => getFeatures(...args) },
  authApi: { getMe: (...args: unknown[]) => getMe(...args) }
}))

// The counts are not what this file tests, and they fetch every database.
vi.mock('@/stores/counts', () => ({
  useCountsStore: () => ({ fetch: vi.fn(), counts: {} })
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ path: '/', fullPath: '/' })
}))

// A local instance rather than `@/plugins/i18n`: the plugin reads localStorage at
// import time, which the test environment does not provide.
const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })

function mountSidebar(contributions: boolean) {
  getFeatures.mockResolvedValue({ data: { contributions } })
  return mount(AppSidebar, {
    props: { open: true, dark: false },
    global: {
      plugins: [i18n],
      stubs: { RouterLink: { template: '<a><slot /></a>' }, VIcon: true, LanguageToggle: true }
    }
  })
}

async function sections(contributions: boolean): Promise<string[]> {
  const wrapper = mountSidebar(contributions)
  await flushPromises()
  return wrapper.findAll('.sidebar-section').map((node) => node.text())
}

async function links(): Promise<string[]> {
  const wrapper = mountSidebar(true)
  await flushPromises()
  return wrapper.findAll('.sidebar-link').map((node) => node.text())
}

function signedInAs(role: string): void {
  getMe.mockResolvedValue({
    data: { user: { id: 'u1', email: 'ada@example.edu', display_name: 'Ada', role } }
  })
}

describe('AppSidebar and CONTRIBUTIONS_ENABLED', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    getMe.mockResolvedValue({ data: { user: null } })
  })

  it('shows contribute and account when contributions are on', async () => {
    expect(await sections(true)).toEqual(expect.arrayContaining(['Contribute', 'Account']))
  })

  it('hides all three when contributions are off', async () => {
    const shown = await sections(false)
    expect(shown).toContain('Reference')
    expect(shown).not.toContain('Contribute')
    expect(shown).not.toContain('Curation')
    expect(shown).not.toContain('Account')
  })
})

describe('AppSidebar and roles (#248)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('hides the review queue from a visitor and a contributor', async () => {
    getMe.mockResolvedValue({ data: { user: null } })
    expect(await sections(true)).not.toContain('Curation')

    setActivePinia(createPinia())
    signedInAs('contributor')
    expect(await sections(true)).not.toContain('Curation')
  })

  it('shows the review queue to a curator, but not the admin page', async () => {
    signedInAs('curator')
    expect(await sections(true)).toContain('Curation')
    expect(await links()).not.toContain('Administration')
  })

  it('shows both to an admin', async () => {
    signedInAs('admin')
    expect(await sections(true)).toContain('Curation')
    expect(await links()).toContain('Administration')
  })
})
