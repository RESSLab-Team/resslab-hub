import {
  computeUvcStress,
  uvcCalibrationError,
  uvcModelCurve,
  uvcParametersFrom
} from '@/utils/material'
import { describe, expect, it } from 'vitest'

// Updated-Voce-Chaboche stress integration. With no hardening (Q=b=D=a=0 and no
// backstresses) the model reduces to elastic-perfectly-plastic, which gives
// closed-form expectations we can pin without re-deriving the solver.
describe('material.computeUvcStress', () => {
  const E = 200000
  const yieldStress = 400

  it('stays elastic below yield: stress = E * cumulative strain', () => {
    const track = computeUvcStress([0.001, 0.002], E, yieldStress, 0, 0, 0, 0, [])
    expect(track).toHaveLength(2)
    expect(track[0]).toBeCloseTo(0, 6)
    // second increment of 0.001 -> 200 MPa, still below the 400 MPa yield
    expect(track[1]).toBeCloseTo(200, 6)
  })

  it('caps at the yield stress once strain exceeds yield (perfect plasticity)', () => {
    const track = computeUvcStress([0, 0.004], E, yieldStress, 0, 0, 0, 0, [])
    expect(track).toHaveLength(2)
    expect(track[0]).toBeCloseTo(0, 6)
    expect(track[1]).toBeCloseTo(yieldStress, 4)
  })
})

// A full parameter set as the review screen sees it: strings straight out of a
// submitted CSV row, with the elastic modulus in GPa (dictionary column since
// #308).
const CELLS: Record<string, string> = {
  uvc_e__gpa_: '181.05',
  uvc_sigma__mpa_: '411.11',
  uvc_q__mpa_: '116.38',
  uvc_b: '16.57',
  uvc_d__mpa_: '131.87',
  uvc_a: '188.03',
  uvc_c1__mpa_: '21161.27',
  uvc_g1: '210.44',
  uvc_c2__mpa_: '1706.61',
  uvc_g2: '16.5',
  uvc_phi__prct_: '5.45'
}

describe('material.uvcParametersFrom', () => {
  it('reads string cells and converts the modulus from GPa to MPa', () => {
    const parameters = uvcParametersFrom(CELLS)
    expect(parameters).not.toBeNull()
    expect(parameters!.e).toBeCloseTo(181050, 6)
    expect(parameters!.sigma).toBe(411.11)
    expect(parameters!.gamma1).toBe(210.44)
    expect(parameters!.gamma2).toBe(16.5)
  })

  it('reads the typed API model, where the cells are numbers', () => {
    const row = Object.fromEntries(
      Object.entries(CELLS).map(([key, value]) => [key, Number(value)])
    )
    expect(uvcParametersFrom(row)).toEqual(uvcParametersFrom(CELLS))
  })

  it('accepts a parameter that is legitimately zero', () => {
    expect(uvcParametersFrom({ ...CELLS, uvc_d__mpa_: '0' })?.d).toBe(0)
  })

  it.each(['', 'NR', 'n/a'])('returns null when a parameter reads %p', (raw) => {
    expect(uvcParametersFrom({ ...CELLS, uvc_q__mpa_: raw })).toBeNull()
  })

  it('returns null when a parameter is missing altogether', () => {
    const rest = { ...CELLS }
    delete rest.uvc_g2
    expect(uvcParametersFrom(rest)).toBeNull()
  })
})

describe('material.uvcCalibrationError', () => {
  it('reads the normalized error', () => {
    expect(uvcCalibrationError(CELLS)).toBe(5.45)
  })

  it('is null when not reported', () => {
    expect(uvcCalibrationError({ ...CELLS, uvc_phi__prct_: 'NR' })).toBeNull()
    expect(uvcCalibrationError({})).toBeNull()
  })
})

describe('material.uvcModelCurve', () => {
  it('pairs each strain with its modelled stress', () => {
    const strain = [0, 0.002, 0.004, 0.002]
    const curve = uvcModelCurve(strain, uvcParametersFrom(CELLS)!)
    expect(curve).toHaveLength(strain.length)
    expect(curve.map((point) => point[0])).toEqual(strain)
    // Below yield the response is elastic: 0.002 * 181050 MPa.
    expect(curve[1][1]).toBeCloseTo(362.1, 1)
    // Past yield the stress must stay under the elastic extrapolation.
    expect(curve[2][1]).toBeLessThan(0.004 * 181050)
  })
})
