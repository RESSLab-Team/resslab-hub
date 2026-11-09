import { databases, navGroups, tools } from '@/utils/navigation'
import { describe, expect, it, vi } from 'vitest'

// A local i18n with both locales: the real plugin reads localStorage at import.
const i18n = vi.hoisted(() => ({ value: null as unknown as ReturnType<typeof createI18n> }))
vi.mock('@/plugins/i18n', async () => {
  const { createI18n } = await import('vue-i18n')
  const { default: en } = await import('@/locales/en.json')
  const { default: fr } = await import('@/locales/fr.json')
  i18n.value = createI18n({ legacy: false, locale: 'en', messages: { en, fr } })
  return { default: i18n.value }
})
import type { createI18n } from 'vue-i18n'

describe('navigation lists', () => {
  it('follow the current locale on each call (no reload needed)', () => {
    const locale = i18n.value.global.locale as unknown as { value: string }
    locale.value = 'en'
    const english = navGroups()[0].name
    const englishTool = tools()[0].name
    locale.value = 'fr'
    expect(navGroups()[0].name).not.toBe(english)
    expect(tools()[0].name).not.toBe(englishTool)
    locale.value = 'en'
    expect(navGroups()[0].name).toBe(english)
  })

  it('names a group database page after its group, in any locale', () => {
    const locale = i18n.value.global.locale as unknown as { value: string }
    for (const value of ['en', 'fr']) {
      locale.value = value
      const groups = navGroups()
      const entries = databases()
      expect(entries.find((entry) => entry.id === 'braces')?.name).toBe(
        groups.find((group) => group.id === 'braces')?.name
      )
      const cyclic = groups.find((group) => group.id === 'materials')?.children[0].name
      expect(entries.find((entry) => entry.id === 'cyclic')?.name).toBe(cyclic)
    }
    locale.value = 'en'
  })
})
