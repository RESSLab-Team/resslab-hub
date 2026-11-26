import i18n from '@/plugins/i18n'
import {
  formatFloat,
  formatNumber,
  formatString,
  isIntegerType,
  missingLabel
} from '@/utils/formatter'
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

  it('formats a float with one decimal by default (#454)', () => {
    expect(formatNumber(record, 'ratio')).toBe('3.1')
    expect(formatNumber(record, 'f_yn')).toBe('345.0')
  })

  it('keeps an integer column an integer, from the dictionary type', () => {
    expect(formatNumber(record, 'f_yn', 1, 'SmallInteger')).toBe('345')
    expect(formatNumber(record, 'f_yn', 1, 'Integer')).toBe('345')
    expect(formatNumber(record, 'f_yn', 1, 'DecimalFloat')).toBe('345.0')
  })

  it('honours the requested number of fraction digits', () => {
    expect(formatNumber(record, 'ratio', 2)).toBe('3.14')
  })

  it('coerces numeric strings (Pydantic v2 serializes Decimal as a string)', () => {
    expect(formatNumber(record, 'text', 1)).toBe('2.5')
  })
})

describe('formatter.formatFloat (#454)', () => {
  it('gives one decimal to a value of 1 or more', () => {
    expect(formatFloat(345)).toBe('345.0')
    expect(formatFloat(40.608028)).toBe('40.6')
    expect(formatFloat(-75.376194)).toBe('-75.4')
    expect(formatFloat(6.35)).toBe('6.3')
    expect(formatFloat(0)).toBe('0.0')
  })

  it('keeps two significant digits for a value under 1', () => {
    expect(formatFloat(0.003)).toBe('0.003')
    expect(formatFloat(0.0456)).toBe('0.046')
    expect(formatFloat(-0.0021)).toBe('-0.0021')
    expect(formatFloat(0.5)).toBe('0.5')
    expect(formatFloat(0.25)).toBe('0.25')
    expect(formatFloat(0.999)).toBe('1.0')
  })

  it('takes the digits asked as a minimum', () => {
    expect(formatFloat(3.14159, 3)).toBe('3.142')
    expect(formatFloat(0.00213, 5)).toBe('0.00213')
    expect(formatFloat(0.003, 2)).toBe('0.003')
    expect(formatFloat(0.5, 2)).toBe('0.50')
  })

  it('stops at six decimals', () => {
    expect(formatFloat(0.0000001234)).toBe('0.0')
  })
})

describe('formatter.isIntegerType', () => {
  it('knows the integer types of the dictionaries', () => {
    for (const type of ['SmallInteger', 'Integer', 'BigInteger', 'SmallSmallInteger']) {
      expect(isIntegerType(type)).toBe(true)
    }
    for (const type of ['DecimalFloat', 'Numeric', 'String', undefined]) {
      expect(isIntegerType(type)).toBe(false)
    }
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
