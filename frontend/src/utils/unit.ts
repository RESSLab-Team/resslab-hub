import i18n from '@/plugins/i18n'
import type { ToggleItem } from '@/utils/toggle'

export type UnitSystem = 'metric' | 'imperial'

/** A function, not a constant, so the labels follow the current locale. */
export function unitItems(): ToggleItem<UnitSystem>[] {
  return [
    { value: 'metric', text: i18n.global.t('enum.metric') },
    { value: 'imperial', text: i18n.global.t('enum.imperial') }
  ]
}

export interface Unit {
  system: string
  referenceUnit: string
  unit: string
  ratio: number
}

export const units: Unit[] = [
  {
    system: 'imperial',
    referenceUnit: 'mm',
    unit: 'in',
    ratio: 25.4 // https://en.wikipedia.org/wiki/Inch
  },
  {
    system: 'imperial',
    referenceUnit: 'mm<sup>3</sup>',
    unit: 'in<sup>3</sup>',
    ratio: Math.pow(25.4, 3) // https://en.wikipedia.org/wiki/Inch
  },
  {
    system: 'imperial',
    referenceUnit: 'mm<sup>4</sup>',
    unit: 'in<sup>4</sup>',
    ratio: Math.pow(25.4, 4) // https://en.wikipedia.org/wiki/Inch
  },
  {
    system: 'imperial',
    referenceUnit: 'MPa',
    unit: 'ksi',
    ratio: 6.894757 // https://en.wikipedia.org/wiki/Pound_per_square_inch
  },
  {
    system: 'imperial',
    referenceUnit: 'kN⋅mm',
    unit: 'kips⋅in',
    ratio: 4.44822 * 25.4 // https://en.wikipedia.org/wiki/Kip_(unit)
  },
  {
    system: 'imperial',
    referenceUnit: '<sup>kN⋅mm</sup>/<sub>rad</sub>',
    unit: '<sup>kips⋅in</sup>/<sub>rad</sub>',
    ratio: 4.44822 * 25.4 // https://en.wikipedia.org/wiki/Kip_(unit)
  }
]
