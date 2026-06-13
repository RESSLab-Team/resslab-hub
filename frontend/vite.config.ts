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
  }
})
