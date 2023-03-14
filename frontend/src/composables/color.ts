import { primaryColor, type Color } from '@/utils/vuetify'
import { computed } from 'vue'

export function useColor(color: Color = primaryColor) {
  return {
    baseColor: computed(() => color?.base),
    lightenColor: computed(() => color?.lighten4),
    darkenColor: computed(() => color?.darken4)
  }
}
