/**
 * Chart palette primitives. Dependency-free so the color scale (and its tests)
 * can be imported without dragging in the i18n/Vuetify plugins.
 */
import hexRgb from 'hex-rgb'

/** Multi-hue categorical palette: the designer's Option 1 from #388, in slot order.
    It replaced Okabe–Ito, which collaborators found too loud. It is less safe for
    colour-blind readers (blue, lavender, violet and slate sit close for red-blind
    eyes), so the slots are handed out by frequency: the closest pairs involve
    slot 7, which only the rarest values reach.
    Brand red stays reserved for selection/emphasis and is never a series color.
    Dashboard charts never index this by position: a value's slot comes from
    `utils/categoryColors.ts`, so it survives filtering and matches across charts. */
export const colorPalette: string[] = [
  '#6288BE', // blue
  '#F6C770', // amber
  '#9EDEC2', // mint
  '#D08DB1', // pink
  '#CCCAFD', // lavender
  '#EB888C', // coral
  '#AC9EDA', // violet
  '#787496' // slate grey
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
