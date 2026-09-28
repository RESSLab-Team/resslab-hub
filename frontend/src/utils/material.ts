import { clone, fill, sum, zip } from 'lodash'

/**
 * https://github.com/ahartloper/RESSPyLab/blob/master/RESSPyLab/uvc_model.py
 */
export function computeUvcStress(
  eTrue: number[], // strain
  E: number,
  sy_0: number,
  Q: number,
  b: number,
  D: number,
  a: number,
  backstresses: { c: number; gamma: number }[],
  tol = 1.0e-8,
  maximum_iterations = 1000
): number[] {
  const alpha_components = fill(Array(backstresses.length), 0)
  let stress = 0
  let ep_eq = 0

  const loading = [0, ...discreteDifference(eTrue)]
  const stress_track = loading.map((strain_inc) => {
    const alpha = sum(alpha_components)
    const yield_stress = sy_0 + Q * (1 - Math.exp(-b * ep_eq)) - D * (1 - Math.exp(-a * ep_eq))

    const trial_stress = stress + E * strain_inc
    const relative_stress = trial_stress - alpha
    const flow_dir = Math.sign(relative_stress)

    const yield_condition = Math.abs(relative_stress) - yield_stress
    let is_converged = yield_condition <= tol

    // Return mapping if plastic loading
    const ep_eq_init = ep_eq
    const alpha_init = alpha
    let consist_param = 0
    let number_of_iterations = 0
    while (!is_converged && number_of_iterations < maximum_iterations) {
      number_of_iterations += 1
      // Isotropic hardening and isotropic modulus
      const yield_stress = sy_0 + Q * (1 - Math.exp(-b * ep_eq)) - D * (1 - Math.exp(-a * ep_eq))
      const iso_modulus = Q * b * Math.exp(-b * ep_eq) - D * a * Math.exp(-a * ep_eq)

      // Kinematic hardening and kinematic modulus
      let alpha = 0
      let kin_modulus = 0
      backstresses.forEach((k, i) => {
        const e_k = Math.exp(-k.gamma * (ep_eq - ep_eq_init))
        alpha +=
          (flow_dir * k.c) / k.gamma + (alpha_components[i] - (flow_dir * k.c) / k.gamma) * e_k
        kin_modulus += k.c * e_k - flow_dir * k.gamma * e_k * alpha_components[i]
      })
      const delta_alpha = alpha - alpha_init

      // Local Newton step
      const numerator =
        Math.abs(relative_stress) - (consist_param * E + yield_stress + flow_dir * delta_alpha)
      const denominator = -(E + iso_modulus + kin_modulus)
      consist_param = consist_param - numerator / denominator
      ep_eq = ep_eq_init + consist_param

      if (Math.abs(numerator) < tol) {
        is_converged = true
      }
    }

    // Update the variables
    stress = trial_stress - E * flow_dir * consist_param
    backstresses.forEach((k, i) => {
      const e_k = Math.exp(-k.gamma * (ep_eq - ep_eq_init))
      alpha_components[i] =
        (flow_dir * k.c) / k.gamma + (alpha_components[i] - (flow_dir * k.c) / k.gamma) * e_k
    })

    if (number_of_iterations >= maximum_iterations) {
      throw new Error(`Return mapping did not converge in ${maximum_iterations} iterations.`)
    }

    return stress
  })

  return stress_track
}

/**
 * https://numpy.org/doc/stable/reference/generated/numpy.diff.html
 */
function discreteDifference(a: number[]): number[] {
  const values = clone(a)
  values.shift()
  return zip(a, values).flatMap(([a, b]) => (a !== undefined && b !== undefined ? [b - a] : []))
}

/**
 * The ten UVC parameters the model needs, all in MPa where they carry a stress
 * unit. `e` is already converted from the dictionary's GPa column.
 */
export interface UvcParameters {
  e: number
  sigma: number
  q: number
  b: number
  d: number
  a: number
  c1: number
  gamma1: number
  c2: number
  gamma2: number
}

/** Dictionary column of each parameter, in the order `computeUvcStress` wants. */
const UVC_COLUMNS: Record<keyof UvcParameters, string> = {
  e: 'uvc_e__gpa_',
  sigma: 'uvc_sigma__mpa_',
  q: 'uvc_q__mpa_',
  b: 'uvc_b',
  d: 'uvc_d__mpa_',
  a: 'uvc_a',
  c1: 'uvc_c1__mpa_',
  gamma1: 'uvc_g1',
  c2: 'uvc_c2__mpa_',
  gamma2: 'uvc_g2'
}

/** Column holding the normalized calibration error, Hartloper et al. (2021) Eq. (33). */
const UVC_PHI_COLUMN = 'uvc_phi__prct_'

/**
 * A cell as a finite number, or null. Handles both shapes the app carries a
 * coupon row in: the typed API model (numbers, null) and a submitted CSV row
 * (strings, with '' and 'NR' meaning "not reported").
 */
function numericCell(raw: unknown): number | null {
  if (typeof raw === 'number') return Number.isFinite(raw) ? raw : null
  if (typeof raw !== 'string') return null
  const value = raw.trim()
  if (value === '' || value === 'NR') return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

/**
 * The UVC parameters of a cyclic-coupon row, or null when one is missing or not
 * numeric. Works on a stored `MaterialModel` and on a submitted row's cells.
 *
 * This is the only place where the dictionary's `uvc_e__gpa_` (GPa since #308)
 * becomes the MPa `computeUvcStress` expects.
 */
export function uvcParametersFrom(row: Record<string, unknown>): UvcParameters | null {
  const parameters = {} as UvcParameters
  for (const [key, column] of Object.entries(UVC_COLUMNS) as [keyof UvcParameters, string][]) {
    const value = numericCell(row[column])
    if (value === null) return null
    parameters[key] = key === 'e' ? value * 1000 : value
  }
  return parameters
}

/**
 * Columns the reviewer would otherwise see nothing about: the ones the model
 * needs but this row does not carry, in dictionary order. Empty when the model
 * can run.
 *
 * A submission opened before a dictionary rename is the common case (#308
 * turned `uvc_e__mpa_` into `uvc_e__gpa_`), and the old column is deliberately
 * NOT read as a fallback: the two names declare different units, so guessing
 * would draw a curve that is wrong by a factor of 1000.
 */
export function missingUvcColumns(row: Record<string, unknown>): string[] {
  return Object.values(UVC_COLUMNS).filter((column) => numericCell(row[column]) === null)
}

/** The row's calibration error in %, or null when it is not reported. */
export function uvcCalibrationError(row: Record<string, unknown>): number | null {
  return numericCell(row[UVC_PHI_COLUMN])
}

/**
 * The model response over a strain history, as `[strain, stress]` points ready
 * for a line chart. Throws what `computeUvcStress` throws when the return
 * mapping does not converge.
 */
export function uvcModelCurve(strain: number[], parameters: UvcParameters): number[][] {
  const stress = computeUvcStress(
    strain,
    parameters.e,
    parameters.sigma,
    parameters.q,
    parameters.b,
    parameters.d,
    parameters.a,
    [
      { c: parameters.c1, gamma: parameters.gamma1 },
      { c: parameters.c2, gamma: parameters.gamma2 }
    ]
  )
  return zip(strain, stress).flatMap(([e, s]) =>
    e !== undefined && s !== undefined ? [[e, s]] : []
  )
}
