import {
  getBraceImage,
  getColumnImage,
  getColumnMapImage,
  getConnectionSpecimenImage,
  getConnectionTypeImage,
  getDuctileFractureSpecimenImage,
  getEbfImage,
  getHSSColumnImage,
  getResidualStressImage,
  getResidualStressSchematic
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

describe('component.getConnectionTypeImage', () => {
  it('slugs the connection type into its sketch', () => {
    expect(getConnectionTypeImage('WUF-W')).toMatch(/img\/connection-type\/wuf-w\.svg$/)
    expect(getConnectionTypeImage('RBS')).toMatch(/img\/connection-type\/rbs\.svg$/)
  })
})

describe('component.getDuctileFractureSpecimenImage', () => {
  it('maps each specimen geometry to its sketch', () => {
    expect(getDuctileFractureSpecimenImage('CNT')).toMatch(/img\/ductile-fracture\/cnt\.png$/)
    expect(getDuctileFractureSpecimenImage('GP')).toMatch(/img\/ductile-fracture\/gp\.png$/)
  })

  it('has no sketch for an unknown geometry', () => {
    expect(getDuctileFractureSpecimenImage('DEMO-SPEC-01')).toBeUndefined()
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

describe('component.getResidualStressSchematic', () => {
  it('keeps the hot-rolled sketch for a hot-rolled record', () => {
    expect(
      getResidualStressSchematic({ profile_type: 'Hot-rolled wide flange', sym: 'doubly' })
    ).toMatch(/img\/residuals\/detail\.png$/)
  })

  it.each([
    ['doubly', 'Flame-cut', 'built-up-doubly-flame.svg'],
    ['doubly', 'Shear-cut', 'built-up-doubly-no-flame.svg'],
    ['mono', 'Flame-cut', 'built-up-mono-flame.svg'],
    ['mono', 'Wire-cut', 'built-up-mono-no-flame.svg'],
    ['doubly', 'Not reported', 'built-up-doubly-no-flame.svg']
  ])('picks the %s / %s sketch of a built-up record', (sym, cut, file) => {
    const image = getResidualStressSchematic({
      profile_type: 'Built-up wide flange',
      sym,
      plt_cut_f: cut
    })
    expect(image.endsWith(`img/residuals/${file}`)).toBe(true)
  })
})
