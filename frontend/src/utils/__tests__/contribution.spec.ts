import { fieldDisplay, prettify } from '@/utils/contribution'
import { describe, expect, it, vi } from 'vitest'

// A local i18n instance: the real plugin reads localStorage at import time.
vi.mock('@/plugins/i18n', async () => {
  const { createI18n } = await import('vue-i18n')
  const messages = { en: { connection: { beam_section: 'Beam section' } } }
  return { default: createI18n({ legacy: false, locale: 'en', messages }) }
})

describe('prettify', () => {
  it('turns a column name into words', () => {
    expect(prettify('d_pz')).toBe('D pz')
  })
})

describe('fieldDisplay', () => {
  it('prefers the translation, even when the column has a symbol', () => {
    expect(fieldDisplay('connections', 'beam_section', 'b<sub>s</sub>')).toBe('Beam section')
  })

  it('uses the dictionary symbol, markup included, when there is no translation', () => {
    expect(fieldDisplay('connections', 'd_pz', 'd<sub>pz</sub>')).toBe('d<sub>pz</sub>')
  })

  it('falls back to the prettified name without a translation or a symbol', () => {
    expect(fieldDisplay('connections', 'd_pz')).toBe('D pz')
    expect(fieldDisplay('connections', 'd_pz', '  ')).toBe('D pz')
  })

  it('ignores a symbol written as LaTeX or code', () => {
    expect(fieldDisplay('tensile', 'pid_force_p', 'K_p')).toBe('Pid force p')
    expect(fieldDisplay('tensile', 'uniform_elongation', '\\varepsilon_u')).toBe(
      'Uniform elongation'
    )
    expect(fieldDisplay('tensile', 'fy_n', 'f_{y,n}')).toBe('Fy n')
  })
})
