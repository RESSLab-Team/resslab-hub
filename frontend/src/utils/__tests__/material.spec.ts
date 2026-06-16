import { computeUvcStress } from '@/utils/material'
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
