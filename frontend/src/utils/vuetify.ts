import { Color } from "vuetify/lib/util/colors";

export const booleanOptions = [true, false];

// https://vuetifyjs.com/en/api/v-select/#props-items
interface SelectItemObject {
  text: string | number;
  value: string | number;
  disabled: boolean;
  divider: boolean;
  header: string;
}

export type SelectItem = string | SelectItemObject;

export function getColorPalette(color: Color): string[] {
  return [
    color.darken4,
    color.darken2,
    color.base,
    color.lighten2,
    color.lighten4,
    color.darken3,
    color.darken1,
    color.lighten1,
    color.lighten3,
    color.lighten5,
  ];
}
