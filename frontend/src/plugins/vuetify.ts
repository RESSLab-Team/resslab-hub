import { createVuetify } from 'vuetify'
import { aliases, mdi } from 'vuetify/iconsets/mdi-svg'
import { VDataTableFooter, VDataTableServer } from 'vuetify/labs/VDataTable'
import 'vuetify/styles'

export default createVuetify({
  components: {
    VDataTableFooter,
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
          accent: '#00A79F' // EPFL leman
        }
      }
    }
  }
})
