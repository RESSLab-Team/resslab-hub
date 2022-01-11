import colors, { Color } from "vuetify/lib/util/colors";

export const booleanOptions = [true, false];

// https://vuetifyjs.com/en/api/v-select/#props-items
interface SelectItemObject {
  // eslint-disable-next-line @typescript-eslint/ban-types
  text: string | number | object;
  // eslint-disable-next-line @typescript-eslint/ban-types
  value: string | number | object;
  disabled?: boolean;
  divider?: boolean;
  header?: string;
}

export type SelectItem = string | SelectItemObject;

export function getColorPalette(color: Color, count: number): string[] {
  switch (count) {
    case 1:
      return [color.base];
    case 2:
      return [color.darken3, color.lighten3];
    case 3:
      return [color.darken4, color.base, color.lighten4];
    case 4:
    case 5:
      return [
        color.darken4,
        color.darken2,
        color.base,
        color.lighten2,
        color.lighten4,
      ];
    default:
      return [
        color.darken4,
        color.darken3,
        color.darken2,
        color.darken1,
        color.base,
        color.lighten1,
        color.lighten2,
        color.lighten3,
        color.lighten4,
      ];
  }
}

export const primaryColor = colors.blue;
export const secondaryColor = colors.red;
