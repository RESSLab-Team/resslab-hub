import en from '@/locales/en.json'
import { LocalStorageKey } from '@/utils/localStorage'
import { createI18n } from 'vue-i18n'

const i18n = createI18n({
  legacy: false,
  locale: localStorage.getItem(LocalStorageKey.Locale) ?? 'en',
  fallbackLocale: 'en',
  messages: {
    en: en
  }
})

export default i18n
