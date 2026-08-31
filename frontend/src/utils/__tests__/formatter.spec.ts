import i18n from '@/plugins/i18n'
import { formatNumber, formatString } from '@/utils/formatter'
import { describe, expect, it } from 'vitest'

const notApplicable = i18n.global.t('enum.notApplicable')
const notReported = i18n.global.t('enum.notReported')

describe('formatter.formatNumber', () => {
  it('returns "not applicable" for null and undefined', () => {
    expect(formatNumber(null as unknown as number)).toBe(notApplicable)
    expect(formatNumber(undefined)).toBe(notApplicable)
  })

  it('returns "not reported" when the value is not a number', () => {
    expect(formatNumber('abc' as unknown as number)).toBe(notReported)
  })

  it('formats numbers with the default of zero fraction digits', () => {
    expect(formatNumber(3.14159)).toBe('3')
  })

  it('honours the requested number of fraction digits', () => {
    expect(formatNumber(3.14159, 2)).toBe('3.14')
  })

  it('coerces numeric strings (Pydantic v2 serializes Decimal as a string)', () => {
    expect(formatNumber('2.5' as unknown as number, 1)).toBe('2.5')
  })
})

describe('formatter.formatString', () => {
  it('returns "not applicable" for null and undefined', () => {
    expect(formatString(null as unknown as string)).toBe(notApplicable)
    expect(formatString(undefined)).toBe(notApplicable)
  })

  it('maps the sentinel "NR" to "not reported"', () => {
    expect(formatString('NR')).toBe(notReported)
  })

  it('passes through any other string unchanged', () => {
    expect(formatString('S355')).toBe('S355')
  })
})
