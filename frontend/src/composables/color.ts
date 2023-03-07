import { primaryColor } from "@/utils/vuetify";
import { computed } from "vue";
import { Color } from "vuetify/lib/util/colors";

export function useColor(color: Color = primaryColor) {
  return {
    baseColor: computed(() => color?.base),
    lightenColor: computed(() => color?.lighten4),
    darkenColor: computed(() => color?.darken4),
  };
}
