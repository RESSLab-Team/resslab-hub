/**
 * Chart palette primitives. Dependency-free so the color scale (and its tests)
 * can be imported without dragging in the i18n/Vuetify plugins.
 */
import hexRgb from 'hex-rgb'

/** Multi-hue categorical palette — Okabe–Ito (colorblind-safe), handoff order.
    Brand red stays reserved for selection/emphasis and is never a series color.
    Dashboard charts never index this by position: a value's slot comes from
    `utils/categoryColors.ts`, so it survives filtering and matches across charts. */
export const colorPalette: string[] = [
  '#0072B2', // blue
  '#E69F00', // amber
  '#009E73', // green
  '#CC79A7', // reddish purple
  '#56B4E9', // sky
  '#D55E00', // vermillion
  '#5B6B78', // slate
  '#332288' // indigo
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
