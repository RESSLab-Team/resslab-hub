import App from '@/App.vue'
import '@/assets/main.scss'
import '@/assets/styles/app.css'
import '@/assets/styles/chart-colors.css'
import '@/assets/styles/epfl-tokens.css'
import '@/assets/styles/fonts.css'
import '@/assets/styles/tool-pages.css'
import { echartsTheme } from '@/plugins/echarts-theme'
import { options } from '@/plugins/gtag'
import i18n from '@/plugins/i18n'
import vuetify from '@/plugins/vuetify'
import router from '@/router'
import '@fontsource/roboto'
import { createPinia } from 'pinia'
import { createApp } from 'vue'
import { THEME_KEY } from 'vue-echarts'
import VueGtag from 'vue-gtag'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(vuetify)
app.use(i18n)
app.use(VueGtag, options, router)

// Brutalist ECharts theme applied to every <v-chart> app-wide.
app.provide(THEME_KEY, echartsTheme)

app.mount('#app')
