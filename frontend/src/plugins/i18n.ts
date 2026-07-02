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

// Only the default locale ships in the entry bundle. French is loaded in
// main.ts's bootstrap *before* mount when it's the active locale — it must be
// registered pre-mount because module-scope strings (nav, chart axis labels)
// resolve via i18n.global.t at import time, which is also why LanguageToggle
// reloads the page on switch instead of swapping messages live.
const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale: initialLocale,
  fallbackLocale: 'en',
  messages: {
    en: en
  }
})

export default i18n
