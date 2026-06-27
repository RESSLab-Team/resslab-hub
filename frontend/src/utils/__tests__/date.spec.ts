import { mapDateToNumber, mapNumberToDate } from '@/utils/date'
import { describe, expect, it } from 'vitest'

// The chart axes work in "days since the Unix epoch": a date string maps to a
// day index and back. 2021-01-01 is 18628 days after 1970-01-01.
describe('date.mapDateToNumber', () => {
  it('converts an ISO date to whole days since the epoch', () => {
    expect(mapDateToNumber('1970-01-01')).toBe(0)
    expect(mapDateToNumber('2021-01-01')).toBe(18628)
  })
})

describe('date.mapNumberToDate', () => {
  it('converts a day index back to an ISO date string', () => {
    expect(mapNumberToDate(0)).toBe('1970-01-01')
    expect(mapNumberToDate(18628)).toBe('2021-01-01')
  })
})

describe('date round-trip', () => {
  it('mapNumberToDate is the inverse of mapDateToNumber', () => {
    expect(mapNumberToDate(mapDateToNumber('2008-09-15'))).toBe('2008-09-15')
  })
})
