import { rl } from '@/assets/icons/databases'
import { createVuetify } from 'vuetify'
import { aliases, mdi } from 'vuetify/iconsets/mdi-svg'
import 'vuetify/styles'

/* Exported so designTokens.spec.ts can check these against the CSS custom
   properties in assets/styles/epfl-tokens.css. Vuetify wants plain hex here
   (it splits them into the rgb triplets behind --v-theme-*), so the brand
   values are written twice on purpose: once as a token, once here. Change one,
   change the other, and the ECharts theme too. See docs/design-system.md. */
export const themes = {
  light: {
    colors: {
      primary: '#E30713', // EPFL rouge (print red — softer-contrast UI target)
      secondary: '#413D3A', // EPFL ardoise
      accent: '#00A79F', // EPFL leman
      background: '#FFFFFF',
      surface: '#FFFFFF'
    }
  },
  dark: {
    dark: true,
    colors: {
      primary: '#E30713',
      secondary: '#A8A8AC',
      accent: '#00A79F',
      background: '#0E0E10',
      surface: '#1A1A1D'
    }
  }
}

export default createVuetify({
  icons: {
    defaultSet: 'mdi',
    aliases,
    sets: {
      mdi,
      rl
    }
  },
  theme: {
    // Emit the runtime theme stylesheet inside `@layer vuetify.theme` so it
    // sits in the same layer block as the rest of Vuetify, below our own
    // layers. Pairs with `$layers: true` in src/settings.scss.
    layers: true,
    themes
  }
})
