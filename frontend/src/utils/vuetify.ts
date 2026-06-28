import i18n from '@/plugins/i18n'
import colormap from 'colormap'
import hexRgb from 'hex-rgb'

export interface Color {
  base: string
  lighten5: string
  lighten4: string
  lighten3: string
  lighten2: string
  lighten1: string
  darken1: string
  darken2: string
  darken3: string
  darken4: string
}

export interface DataOptions {
  sortBy?: {
    key: string
    order: 'asc' | 'desc'
  }[]
  page?: number
  itemsPerPage?: number
}

export const booleanOptions: SelectItemObject<boolean>[] = [
  {
    title: i18n.global.t('enum.true'),
    value: true
  },
  {
    title: i18n.global.t('enum.false'),
    value: false
  }
]

// https://vuetifyjs.com/en/api/v-select/#props-items
export interface SelectItemObject<V = string | number | object> {
  // eslint-disable-next-line @typescript-eslint/ban-types
  title: string | number | object
  value: V
  disabled?: boolean
  divider?: boolean
  header?: string
}

export type SelectItem<V = string | number | object> = string | SelectItemObject<V>

/* ============================================================
   EPFL chart palette — soft pastels (see assets/styles/chart-colors.css).
   Brand red #E30713 is reserved for primary actions and selection
   emphasis; it never appears as a series color.
   ============================================================ */

/** Mix a hex color toward black by `amount` (0..1). */
function darken(hex: string, amount: number): string {
  const { red, green, blue } = hexRgb(hex)
  const mix = (c: number) => Math.round(c * (1 - amount))
  return (
    '#' + [red, green, blue].map((c) => mix(c).toString(16).padStart(2, '0')).join('')
  ).toUpperCase()
}

/** Build a sequential Color ramp from the 5 shades of a pastel hue family
    (darker → lighter), extending the dark end programmatically. */
function family(shades: [string, string, string, string, string]): Color {
  const [darker, dark, base, light, lighter] = shades
  return {
    base: darker,
    lighten1: dark,
    lighten2: base,
    lighten3: light,
    lighten4: lighter,
    lighten5: lighter,
    darken1: darken(darker, 0.12),
    darken2: darken(darker, 0.24),
    darken3: darken(darker, 0.36),
    darken4: darken(darker, 0.48)
  }
}

export const okabeBlue = family(['#0072B2', '#3A93C7', '#6FB2D8', '#A6D0E8', '#D2E7F4'])
export const periwinkle = family(['#A5ADD8', '#BAC0E4', '#CFD4EE', '#D9DEE9', '#E3E8F4'])
export const peach = family(['#FDD279', '#FFDF96', '#FFEBB5', '#FFF4D4', '#FFFBE8'])
export const plum = family(['#C19ACD', '#CFB0DA', '#DDC6E6', '#EADCF1', '#F3ECF7'])
export const apricot = family(['#FABF75', '#FFD093', '#FFE0B3', '#FFE8C4', '#FFF0D5'])
export const mint = family(['#A4D6D5', '#B9E2E1', '#CFEDEC', '#D9F2F1', '#E6F7F6'])
export const yellowgreen = family(['#ABCF84', '#C0DEA0', '#D5EBBE', '#E5F2D4', '#F0F8EA'])
export const mauve = family(['#BBA3CE', '#C8B5D8', '#D5C7E2', '#E2D9EC', '#EDE8F2'])
export const cobalt = family(['#B0B7DE', '#C5CAE9', '#D4D9EC', '#DEE3EF', '#EBEFF9'])
export const sky = family(['#A4BCE3', '#B8CCEC', '#CEDDF4', '#D9E8F8', '#E5F2FC'])

/** Soft-black ink ramp — used for calibrated-model overlays. */
export const ink: Color = {
  base: '#212121',
  lighten1: '#4A4A4A',
  lighten2: '#707070',
  lighten3: '#8E8E8E',
  lighten4: '#C1C1C1',
  lighten5: '#D5D5D5',
  darken1: '#1A1A1A',
  darken2: '#141414',
  darken3: '#0E0E0E',
  darken4: '#080808'
}

/** Test data series lead with Okabe–Ito blue; model overlays follow in ink.
    (Categorical chart hues use the Okabe–Ito colorblind-safe palette.) */
export const primaryColor = okabeBlue
export const secondaryColor = ink

export const primaryColors = [
  okabeBlue,
  ink,
  periwinkle,
  plum,
  sky,
  mint,
  apricot,
  mauve,
  yellowgreen
]

/** Multi-hue categorical palette — Okabe–Ito (colorblind-safe), handoff order.
    Brand red stays reserved for selection/emphasis and is never a series color. */
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

export function getColorPalette(color: Color, count: number): string[] {
  if (count <= 1) {
    return [color.base]
  }
  // Categorical series get distinct pastel hues rather than a single-hue ramp.
  return Array.from({ length: count }, (_, index) => colorPalette[index % colorPalette.length])
}

/** Perceptually-uniform sequential scales for continuous/ordered data
    (fragility families, density ramps). Defaults to viridis; magma/inferno/
    plasma available. `colormap` requires ≥9 shades for these, so we oversample
    and pick `count` evenly-spaced stops (dark → light). */
export type SequentialScale = 'viridis' | 'magma' | 'inferno' | 'plasma'

export function getColorMap(count: number, scale: SequentialScale = 'viridis'): string[] {
  if (count <= 0) return []
  const n = Math.max(count, 16)
  const ramp = colormap<'hex'>({ colormap: scale, nshades: n, format: 'hex' })
  if (count >= n) return ramp
  if (count === 1) return [ramp[0]]
  return Array.from(
    { length: count },
    (_, index) => ramp[Math.round((index * (n - 1)) / (count - 1))]
  )
}
