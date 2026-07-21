import type { DictColumn, DictType } from '@/utils/dictionary'
import { validateCell, validateHeaders, validateSheet } from '@/utils/validation'
import { describe, expect, it } from 'vitest'

function col(type: DictType, nullable = true): DictColumn {
  return { name: 'x', description: '', symbol: '', unit: '-', type, example: '', nullable }
}

describe('validateCell — blank / NR / NA', () => {
  it('blank on a nullable column is accepted', () => {
    expect(validateCell(col('Numeric'), '')).toBeNull()
  })
  it('blank on a required column warns (submitted as NR)', () => {
    expect(validateCell(col('Numeric', false), '')?.level).toBe('warn')
  })
  it('NR is always skipped', () => {
    expect(validateCell(col('Numeric', false), 'NR')).toBeNull()
    expect(validateCell(col('Numeric'), 'nr')).toBeNull()
  })
  it('NA errors only on a non-nullable column', () => {
    expect(validateCell(col('String'), 'NA')).toBeNull()
    expect(validateCell(col('String', false), 'NA')?.level).toBe('error')
  })
})

describe('validateCell — types', () => {
  it('boolean accepts yes/no case-insensitively', () => {
    expect(validateCell(col('Boolean'), 'Yes')).toBeNull()
    expect(validateCell(col('Boolean'), 'NO')).toBeNull()
    expect(validateCell(col('Boolean'), 'maybe')?.level).toBe('error')
  })

  it('integer accepts whole numbers, warns on fractions, errors on text', () => {
    expect(validateCell(col('Integer'), '42')).toBeNull()
    expect(validateCell(col('Integer'), '1e3')).toBeNull()
    expect(validateCell(col('SmallInteger'), '1.5')?.level).toBe('warn')
    expect(validateCell(col('BigInteger'), 'abc')?.level).toBe('error')
  })

  it('decimal/numeric accept numbers and reject NaN/Infinity and text', () => {
    expect(validateCell(col('DecimalFloat'), '3.14')).toBeNull()
    expect(validateCell(col('Numeric'), '-2.5e-3')).toBeNull()
    expect(validateCell(col('Numeric'), 'NaN')?.level).toBe('error')
    expect(validateCell(col('DecimalFloat'), 'Infinity')?.level).toBe('error')
    expect(validateCell(col('Numeric'), 'x')?.level).toBe('error')
  })

  it('date accepts DD.MM.YY and DD.MM.YYYY, rejects bad dates', () => {
    expect(validateCell(col('Date'), '01.01.20')).toBeNull()
    expect(validateCell(col('Date'), '31.12.2020')).toBeNull()
    expect(validateCell(col('Date'), '1.1.20')).toBeNull()
    expect(validateCell(col('Date'), '32.01.2020')?.level).toBe('error')
    expect(validateCell(col('Date'), '29.02.2019')?.level).toBe('error') // not a leap year
    expect(validateCell(col('Date'), '2020-01-01')?.level).toBe('error')
  })

  it('string accepts anything', () => {
    expect(validateCell(col('String'), 'whatever')).toBeNull()
  })
})

describe('validateHeaders', () => {
  it('reports missing and unexpected against the braces dictionary', () => {
    const report = validateHeaders('braces', ['id', 'not_a_real_column'])
    expect(report.unexpected).toContain('not_a_real_column')
    expect(report.missing).toContain('investigator')
    expect(report.missing).not.toContain('id')
  })
})

describe('validateSheet', () => {
  it('flags a missing id and a bad numeric cell', () => {
    const issues = validateSheet('braces', [
      { id: '', area: 'abc' },
      { id: 'B2' }
    ])
    expect(issues.get(0)?.id?.level).toBe('error')
    expect(issues.get(0)?.area?.level).toBe('error')
    expect(issues.get(1)?.id).toBeUndefined()
  })

  it('flags duplicate ids on every offending row', () => {
    const issues = validateSheet('braces', [{ id: 'B1' }, { id: 'B1' }])
    expect(issues.get(0)?.id?.message).toContain('Duplicate')
    expect(issues.get(1)?.id?.message).toContain('Duplicate')
  })
})
