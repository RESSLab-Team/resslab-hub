import { computeCdf, hotspotsFor } from '@/utils/sem'
import { describe, expect, it } from 'vitest'

describe('computeCdf', () => {
  it('sorts input ascending and returns rank/N as the second coordinate', () => {
    expect(computeCdf([3, 1, 2])).toEqual([
      [1, 1 / 3],
      [2, 2 / 3],
      [3, 1]
    ])
  })

  it('returns an empty array for empty input', () => {
    expect(computeCdf([])).toEqual([])
  })

  it('handles a single value', () => {
    expect(computeCdf([0.05])).toEqual([[0.05, 1]])
  })
})

describe('hotspotsFor', () => {
  it('returns 5 CNT hotspots for specimen_type=CNT', () => {
    expect(Object.keys(hotspotsFor('CNT'))).toEqual(['north', 'south', 'east', 'west', 'middle'])
  })

  it('returns 3 GP hotspots for specimen_type=GP', () => {
    expect(Object.keys(hotspotsFor('GP'))).toEqual(['west', 'middle', 'east'])
  })
})
