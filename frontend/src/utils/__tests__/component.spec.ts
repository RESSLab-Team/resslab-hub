import {
  getBraceImage,
  getColumnImage,
  getColumnMapImage,
  getConnectionSpecimenImage,
  getEbfImage,
  getHSSColumnImage,
  getResidualStressImage
} from '@/utils/component'
import { afterEach, describe, expect, it, vi } from 'vitest'

// publicPath is prepended to every asset URL; assert on the suffix so the tests
// don't depend on the base URL the bundler injects.
describe('component.getResidualStressImage', () => {
  it('points at the residual-stress detail image', () => {
    expect(getResidualStressImage()).toMatch(/img\/residuals\/detail\.png$/)
  })
})

describe('component.getConnectionSpecimenImage', () => {
  it('maps each known specimen type to its svg', () => {
    expect(getConnectionSpecimenImage('Exterior - Beam Loaded - Subassembly')).toMatch(
      /exterior-beam\.svg$/
    )
    expect(getConnectionSpecimenImage('Interior - Column Loaded - Subassembly')).toMatch(
      /interior-column\.svg$/
    )
  })

  it('returns an empty string for an unknown specimen type', () => {
    expect(getConnectionSpecimenImage('something else')).toBe('')
  })
})

describe('component.getBraceImage', () => {
  it('maps each boundary condition to its image', () => {
    expect(getBraceImage('Gusset plate')).toMatch(/gusset-plate\.png$/)
    expect(getBraceImage('Pin-Pin end')).toMatch(/pinned-end\.png$/)
  })

  it('returns undefined for an unknown boundary condition', () => {
    expect(getBraceImage('unknown')).toBeUndefined()
  })
})

describe('component.getColumnMapImage', () => {
  it('keys off boundary condition first, then axis of bending', () => {
    expect(getColumnMapImage('Strong', 'Fixed-Fixed')).toMatch(/Fixed_Fixed_StrongAxis\.png$/)
    expect(getColumnMapImage('Weak', 'Fixed-Free')).toMatch(/Fixed_Free_WeakAxis\.png$/)
  })

  it('returns undefined when nothing matches', () => {
    expect(getColumnMapImage('Strong', 'unknown')).toBeUndefined()
  })
})

describe('component.getColumnImage', () => {
  it('maps an axis + boundary combination to its image', () => {
    expect(getColumnImage('Bi-axial', 'Fixed-Flexible', '')).toMatch(/Biaxial_Fixed_Flexible\.png$/)
  })

  it('falls back to the weak-axis image for bidirectional loading', () => {
    expect(getColumnImage('Weak', 'unknown', 'Bidirectional')).toMatch(/Fixed_Free_WeakAxis\.png$/)
  })

  it('returns undefined when nothing matches', () => {
    expect(getColumnImage('unknown', 'unknown', 'unknown')).toBeUndefined()
  })
})

describe('component.getHSSColumnImage', () => {
  it('maps each test configuration to its image', () => {
    expect(getHSSColumnImage('3PB')).toMatch(/3_point_bending\.jpg$/)
    expect(getHSSColumnImage('CF')).toMatch(/cantilever\.jpg$/)
    expect(getHSSColumnImage('DC')).toMatch(/double_curvature\.jpg$/)
  })

  it('warns and returns an empty string for an unknown configuration', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => undefined)
    expect(getHSSColumnImage('ZZ')).toBe('')
    expect(warn).toHaveBeenCalled()
    warn.mockRestore()
  })
})

describe('component.getEbfImage', () => {
  afterEach(() => vi.restoreAllMocks())

  it('maps each link configuration to its numbered image', () => {
    expect(getEbfImage('TF1')).toMatch(/img\/ebf\/EBF_1\.png$/)
    expect(getEbfImage('TF5')).toMatch(/img\/ebf\/EBF_7\.png$/)
  })

  it('warns and returns an empty string for an unknown configuration', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => undefined)
    expect(getEbfImage('nope')).toBe('')
    expect(warn).toHaveBeenCalled()
  })
})
