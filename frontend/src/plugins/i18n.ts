import en from '@/locales/en.json'
import { LocalStorageKey } from '@/utils/localStorage'
import { createI18n } from 'vue-i18n'

export const SUPPORTED_LOCALES = [
  { value: 'en', label: 'EN' },
  { value: 'fr', label: 'FR' }
] as const

const stored = localStorage.getItem(LocalStorageKey.Locale)
export const initialLocale = SUPPORTED_LOCALES.some((l) => l.value === stored)
  ? (stored as string)
  : 'en'

// Only the default locale ships in the entry bundle. The other one is loaded
// on demand (loadLocaleMessages): before mount when it is the stored choice,
// or when the user switches. No module keeps a translated string at import
// time, so a switch re-renders live, with no reload.
const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale: initialLocale,
  fallbackLocale: 'en',
  messages: {
    en: en
  }
})

/** Load and register a locale's messages once. English is always there. */
export async function loadLocaleMessages(locale: string): Promise<void> {
  if ((i18n.global.availableLocales as string[]).includes(locale)) return
  if (locale === 'fr') {
    const fr = await import('@/locales/fr.json')
    i18n.global.setLocaleMessage('fr', fr.default)
  }
}

export default i18n
