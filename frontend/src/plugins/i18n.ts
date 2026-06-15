import en from '@/locales/en.json'
import fr from '@/locales/fr.json'
import { LocalStorageKey } from '@/utils/localStorage'
import { createI18n } from 'vue-i18n'

export const SUPPORTED_LOCALES = [
  { value: 'en', label: 'EN' },
  { value: 'fr', label: 'FR' }
] as const

const stored = localStorage.getItem(LocalStorageKey.Locale)
const locale = SUPPORTED_LOCALES.some((l) => l.value === stored) ? (stored as string) : 'en'

const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale,
  fallbackLocale: 'en',
  messages: {
    en: en,
    fr: fr
  }
})

export default i18n
