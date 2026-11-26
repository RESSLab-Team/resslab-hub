/**
 * Chart palette primitives. Dependency-free so the color scale (and its tests)
 * can be imported without dragging in the i18n/Vuetify plugins.
 */
import hexRgb from 'hex-rgb'

/** Multi-hue categorical palette: Option F of #388 (IBM Carbon), in slot order.
    Dimitrios chose it over Option 1. Carbon made these colours for white text,
    so the white treemap labels read at 5.0:1 or more on every slot.
    Weak point: for red-blind and green-blind readers the navy (slot 2) and the
    violet (slot 8) come close. The slots go by frequency, so slot 8 only goes to
    the 8th most common value of a field. If F does not work out, Option B of #388 is the
    fallback Dimitrios named.
    Brand red stays reserved for selection/emphasis and is never a series color.
    Dashboard charts never index this by position: a value's slot comes from
    `utils/categoryColors.ts`, so it survives filtering and matches across charts. */
export const colorPalette: string[] = [
  '#0072C3', // blue
  '#00539A', // navy
  '#9F1853', // wine
  '#726E6E', // grey
  '#D02670', // magenta
  '#005D5D', // dark teal
  '#8A3FFC', // purple
  '#6929C4' // violet
]

/** Mix hex color `from` toward `to` by `amount` (0 = `from`, 1 = `to`), in sRGB. */
export function blendHex(from: string, to: string, amount: number): string {
  const a = hexRgb(from)
  const b = hexRgb(to)
  const mix = (x: number, y: number) => Math.round(x + (y - x) * amount)
  return (
    '#' +
    [mix(a.red, b.red), mix(a.green, b.green), mix(a.blue, b.blue)]
      .map((c) => c.toString(16).padStart(2, '0'))
      .join('')
  ).toUpperCase()
}
