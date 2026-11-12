import { isNotReported, missingKey } from '@/utils/missing'
import { cellKey } from '@/utils/queryEngine'
import { describe, expect, it } from 'vitest'

const row = { f_um: null, f_um_gp: null, f_yn: 345, steel: 'S355', not_reported: ['f_um'] }

describe('missing', () => {
  it('reads the not_reported list', () => {
    expect(isNotReported(row, 'f_um')).toBe(true)
    expect(isNotReported(row, 'f_um_gp')).toBe(false)
    expect(isNotReported({ f_um: null }, 'f_um')).toBe(false)
    expect(isNotReported({ f_um: null, not_reported: null }, 'f_um')).toBe(false)
  })

  it('gives NR or NA for an empty cell', () => {
    expect(missingKey(row, 'f_um')).toBe('NR')
    expect(missingKey(row, 'f_um_gp')).toBe('NA')
  })
})

describe('cellKey', () => {
  it('keeps NR and NA apart for empty cells', () => {
    expect(cellKey(row, 'f_um')).toBe('NR')
    expect(cellKey(row, 'f_um_gp')).toBe('NA')
    expect(cellKey(row, 'missing_field')).toBe('NA')
  })

  it('formats a value like formatValue', () => {
    expect(cellKey(row, 'f_yn')).toBe('345')
    expect(cellKey(row, 'steel')).toBe('S355')
    expect(cellKey({ flag: true }, 'flag')).toBe('True')
    expect(cellKey({ x: NaN }, 'x')).toBe('NR')
  })
})
