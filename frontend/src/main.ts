import App from '@/App.vue'
import '@/assets/main.scss'
import '@/assets/styles/app.css'
import '@/assets/styles/chart-colors.css'
import '@/assets/styles/epfl-tokens.css'
import '@/assets/styles/tool-pages.css'
import { options } from '@/plugins/gtag'
import vuetify from '@/plugins/vuetify'
import router from '@/router'
import '@fontsource/roboto'
import { createPinia } from 'pinia'
import { createApp } from 'vue'
import VueGtag from 'vue-gtag'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(vuetify)
app.use(VueGtag, options, router)

app.mount('#app')
