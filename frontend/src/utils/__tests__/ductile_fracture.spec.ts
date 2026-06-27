import i18n from '@/plugins/i18n'
import { displayLoading } from '@/utils/ductile_fracture'
import { describe, expect, it } from 'vitest'

const cyclic = i18n.global.t('enum.cyclic')
const monotonic = i18n.global.t('enum.monotonic')

describe('ductile_fracture.displayLoading', () => {
  it('returns an empty string for null/undefined/empty input', () => {
    expect(displayLoading(null)).toBe('')
    expect(displayLoading(undefined)).toBe('')
    expect(displayLoading('')).toBe('')
  })

  it('recognises "cyclic" case-insensitively as a substring', () => {
    expect(displayLoading('Cyclic')).toBe(cyclic)
    expect(displayLoading('CYCLIC loading')).toBe(cyclic)
  })

  it('recognises "monotonic" case-insensitively as a substring', () => {
    expect(displayLoading('Monotonic')).toBe(monotonic)
  })

  it('passes through an unrecognised loading label unchanged', () => {
    expect(displayLoading('Static')).toBe('Static')
  })
})
