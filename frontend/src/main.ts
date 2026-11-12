// First on purpose: index.css declares the cascade layer order, and that
// order is fixed by whichever sheet names a layer first (see index.css).
import '@/assets/styles/index.css'

import App from '@/App.vue'
import { echartsTheme } from '@/plugins/echarts-theme'
import { options } from '@/plugins/gtag'
import i18n, { initialLocale, loadLocaleMessages } from '@/plugins/i18n'
import vuetify from '@/plugins/vuetify'
import router from '@/router'
import { onCookieConsent, showConsentStylesheet } from '@/utils/cookieConsent'
import { createPinia } from 'pinia'
import { createApp } from 'vue'
import VueGtag, { bootstrap as startGtag } from 'vue-gtag'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(vuetify)
app.use(i18n)
app.use(VueGtag, options, router)

// Google Analytics waits for the answer to the EPFL cookie banner (#264):
// options has `bootstrap: false`, so nothing loads before this call.
onCookieConsent(() => void startGtag())
showConsentStylesheet()

// Brutalist ECharts theme applied to every <v-chart> app-wide. 'ecTheme' is
// vue-echarts' THEME_KEY, written as the literal so the entry bundle doesn't
// import vue-echarts — that one import dragged all of echarts/zrender (~⅓ of
// the entry chunk) into the first paint. A unit test pins the literal against
// the real export (echartsThemeKey.spec.ts), so an upgrade can't silently
// break the wiring.
app.provide('ecTheme', echartsTheme)

async function bootstrap(): Promise<void> {
  // The non-default locale loads as its own chunk. Register it before mount,
  // so the first paint is already in the stored language.
  await loadLocaleMessages(initialLocale)
  document.documentElement.lang = initialLocale
  app.mount('#app')
}
bootstrap()
