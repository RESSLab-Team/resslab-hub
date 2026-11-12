import i18n from '@/plugins/i18n'
import { formatNumber, formatString, missingLabel } from '@/utils/formatter'
import { describe, expect, it } from 'vitest'

const notApplicable = i18n.global.t('enum.notApplicable')
const notReported = i18n.global.t('enum.notReported')

// A record as the API sends it: `not_reported` lists the empty number columns
// whose CSV cell was `nr` (#427).
const record = {
  f_yn: 345,
  f_um: null as number | null,
  f_um_gp: null as number | null,
  ratio: 3.14159,
  text: '2.5' as unknown as number,
  bad: 'abc' as unknown as number,
  not_reported: ['f_um']
}

describe('formatter.formatNumber', () => {
  it('says "Not reported" for an empty value the record lists', () => {
    expect(notReported).toBe('Not reported')
    expect(formatNumber(record, 'f_um')).toBe(notReported)
  })

  it('says "Not applicable" for an empty value the record does not list', () => {
    expect(notApplicable).toBe('Not applicable')
    expect(formatNumber(record, 'f_um_gp')).toBe(notApplicable)
  })

  it('says "Not applicable" when the record has no list (data not uploaded again yet)', () => {
    expect(formatNumber({ f_um: null as number | null }, 'f_um')).toBe(notApplicable)
    expect(formatNumber({ f_um: undefined as number | undefined }, 'f_um')).toBe(notApplicable)
  })

  it('returns "not reported" when the value is not a number', () => {
    expect(formatNumber(record, 'bad')).toBe(notReported)
  })

  it('formats numbers with the default of zero fraction digits', () => {
    expect(formatNumber(record, 'ratio')).toBe('3')
    expect(formatNumber(record, 'f_yn')).toBe('345')
  })

  it('honours the requested number of fraction digits', () => {
    expect(formatNumber(record, 'ratio', 2)).toBe('3.14')
  })

  it('coerces numeric strings (Pydantic v2 serializes Decimal as a string)', () => {
    expect(formatNumber(record, 'text', 1)).toBe('2.5')
  })
})

describe('formatter.missingLabel', () => {
  it('follows the not_reported list', () => {
    expect(missingLabel(record, 'f_um')).toBe(notReported)
    expect(missingLabel(record, 'f_um_gp')).toBe(notApplicable)
    expect(missingLabel({}, 'f_um')).toBe(notApplicable)
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
