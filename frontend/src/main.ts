import App from '@/App.vue'
import '@/assets/main.scss'
import '@/assets/styles/app.css'
import '@/assets/styles/chart-colors.css'
import '@/assets/styles/epfl-tokens.css'
import '@/assets/styles/fonts.css'
import '@/assets/styles/tool-pages.css'
import { echartsTheme } from '@/plugins/echarts-theme'
import { options } from '@/plugins/gtag'
import i18n, { initialLocale } from '@/plugins/i18n'
import vuetify from '@/plugins/vuetify'
import router from '@/router'
import { createPinia } from 'pinia'
import { createApp } from 'vue'
import VueGtag from 'vue-gtag'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(vuetify)
app.use(i18n)
app.use(VueGtag, options, router)

// Brutalist ECharts theme applied to every <v-chart> app-wide. 'ecTheme' is
// vue-echarts' THEME_KEY, written as the literal so the entry bundle doesn't
// import vue-echarts — that one import dragged all of echarts/zrender (~⅓ of
// the entry chunk) into the first paint. A unit test pins the literal against
// the real export (echartsThemeKey.spec.ts), so an upgrade can't silently
// break the wiring.
app.provide('ecTheme', echartsTheme)

async function bootstrap(): Promise<void> {
  // The non-default locale loads as its own chunk, but must be registered
  // BEFORE mount: module-scope strings resolve via i18n.global.t at import
  // time (which is also why LanguageToggle reloads the page on switch).
  if (initialLocale === 'fr') {
    const fr = await import('@/locales/fr.json')
    i18n.global.setLocaleMessage('fr', fr.default)
  }
  app.mount('#app')
}
bootstrap()
