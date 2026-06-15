import { createVuetify } from 'vuetify'
import { VDataTableServer } from 'vuetify/components'
import { aliases, mdi } from 'vuetify/iconsets/mdi-svg'
import 'vuetify/styles'

export default createVuetify({
  components: {
    VDataTableServer
  },
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
          primary: '#FF0000', // EPFL rouge
          secondary: '#413D3A', // EPFL ardoise
          accent: '#00A79F', // EPFL leman
          background: '#FFFFFF',
          surface: '#FFFFFF'
        }
      },
      dark: {
        dark: true,
        colors: {
          primary: '#FF0000',
          secondary: '#A8A8AC',
          accent: '#00A79F',
          background: '#0E0E10',
          surface: '#1A1A1D'
        }
      }
    }
  }
})
