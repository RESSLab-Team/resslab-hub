export type Point = [number, number]

/**
 * A model-page input variable: a keyed numeric range with a display label and
 * optional unit. Drives the slider controls on the *Model.vue pages.
 * (Relocated from the now-deleted commons/sliders/UnitSlider.vue.)
 */
export interface Variable<K extends string = string> {
  key: K
  text: string
  unit?: string
  min: number
  max: number
}
