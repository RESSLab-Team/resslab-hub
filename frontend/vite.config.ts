import { dirname, resolve } from 'node:path'
import { fileURLToPath, URL } from 'node:url'

import VueI18nPlugin from '@intlify/unplugin-vue-i18n/vite'
import dsv from '@rollup/plugin-dsv'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'
import vuetify from 'vite-plugin-vuetify'

// Strips the EPFL cookie-consent tags in dev only — their consent cookie is
// scoped to the registrable domain, which the browser rejects on localhost /
// tunnel hosts, so the banner reappears on every load. Production keeps them.
function stripCookieConsentInDev() {
  return {
    name: 'strip-cookie-consent-dev',
    apply: 'serve' as const,
    transformIndexHtml(html: string) {
      return html.replace(/^.*epfl-cookie-consent\.(css|js).*\n?/gm, '')
    }
  }
}

// vite-plugin-vuetify rewrites every <v-...> in a template into a deep import
// (e.g. vuetify/components/VCard). Vite's dep optimizer discovers these lazily
// as each page first renders, and every newly-seen batch triggers a re-optimize
// followed by a full-page reload — the cascade that makes the first dev load
// crawl (and throws transient "chunk does not exist" 404s mid-reload). Listing
// the component MODULES the app uses up front folds them into the initial cold
// pass, so none is discovered late. Sub-components share their parent's module
// (VCardText -> VCard, VCol/VRow/VSpacer -> VGrid, VListItem -> VList,
// VDataTableServer -> VDataTable). We list only used components on purpose:
// blindly including all of vuetify pulls in modules that fail to optimize (e.g.
// the deprecated VOverflowBtn has a broken CSS import). When a new <v-...> tag
// is added, add its module here too; until then it just costs one extra reload.
const VUETIFY_COMPONENTS = [
  'VAlert',
  'VApp',
  'VBtn',
  'VBtnGroup',
  'VBtnToggle',
  'VCard',
  'VCheckbox',
  'VDataTable',
  'VDialog',
  'VDivider',
  'VGrid',
  'VIcon',
  'VImg',
  'VList',
  'VMenu',
  'VRangeSlider',
  'VResponsive',
  'VSelect',
  'VSnackbar',
  'VTable',
  'VTextField',
  'VTooltip'
].map((name) => `vuetify/components/${name}`)

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    stripCookieConsentInDev(),
    vue(),
    vuetify({
      styles: { configFile: 'src/settings.scss' }
    }),
    VueI18nPlugin({
      include: resolve(dirname(fileURLToPath(import.meta.url)), './src/locales/**')
    }),
    dsv({
      processRow: (row) => {
        Object.keys(row).forEach((key) => {
          const value = row[key]
          if (value !== undefined) {
            const numberValue = Number(value)
            const newValue = isNaN(numberValue) ? value : numberValue
            row[key] = newValue as string
          }
        })
        return row
      }
    })
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  // Dev-only startup tuning. Pre-bundle the heavy deps in a single cold pass so
  // Vite never discovers one mid-session and forces a full-page reload, and warm
  // the entry/home modules on boot so the first page is ready sooner. No effect
  // on `vite build`.
  optimizeDeps: {
    include: [
      'vue',
      'vue-router',
      'pinia',
      'axios',
      'vue-i18n',
      'vue-echarts',
      'echarts',
      'mathjs',
      'lodash',
      // Home renders the overview map (lazily), so pre-bundle leaflet too.
      'leaflet',
      'leaflet.markercluster',
      // Every Vuetify component the app uses — the main source of the reload
      // cascade (see VUETIFY_COMPONENTS above). echarts-gl is intentionally left
      // out: it's only on 3D-fragility pages and optimizes on demand there.
      ...VUETIFY_COMPONENTS
    ]
  },
  server: {
    warmup: {
      clientFiles: ['./src/main.ts', './src/App.vue', './src/views/HomeView.vue']
    }
  },
  build: {
    rollupOptions: {
      output: {
        // Pin the heavy, rarely-updated libraries into their own chunks so an
        // app-code edit doesn't rename (and re-download) half a megabyte of
        // framework on every deploy. Without this, rollup smears echarts across
        // whichever app chunks first import it (SimpleTable, UnitChart, ...).
        // echarts-gl/claygl are NOT pinned: they already isolate into the lazy
        // 3D-chart chunk, and pinning them here would load them eagerly with
        // every chart page.
        manualChunks(id: string) {
          if (!id.includes('node_modules')) return undefined
          if (/node_modules\/(echarts|zrender|vue-echarts|resize-detector)\//.test(id)) {
            return 'echarts'
          }
          // Vuetify is deliberately NOT pinned: rollup already splits the
          // route-only components (VSelect, ...) into lazy chunks, and pinning
          // it would pull them all into the eager path.
          if (/node_modules\/(@vue|vue|vue-router|pinia|vue-i18n|@intlify|vue-demi)\//.test(id)) {
            return 'vendor'
          }
          return undefined
        }
      }
    }
  }
})
