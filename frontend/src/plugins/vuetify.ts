import { createVuetify } from 'vuetify'
import { aliases, mdi } from 'vuetify/iconsets/mdi-svg'
import 'vuetify/styles'

export default createVuetify({
  icons: {
    defaultSet: 'mdi',
    aliases,
    sets: {
      mdi
    }
  },
  theme: {
    themes: {
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
  }
})
