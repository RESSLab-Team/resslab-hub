import { withFieldClause } from '@/composables/dashboard'
import { describe, expect, it } from 'vitest'

describe('dashboard.withFieldClause', () => {
  it('appends the clause to an empty query', () => {
    expect(withFieldClause(undefined, 'd_b', '200<<400')).toBe('d_b:200<<400')
  })

  it('replaces an existing clause for the field and keeps the others', () => {
    expect(withFieldClause('steel_b:=A992;d_b:0<<100', 'd_b', '200<<400')).toBe(
      'steel_b:=A992;d_b:200<<400'
    )
  })

  it('drops the clause when the value is undefined', () => {
    expect(withFieldClause('steel_b:=A992;d_b:0<<100', 'd_b', undefined)).toBe('steel_b:=A992')
    expect(withFieldClause('d_b:0<<100', 'd_b', undefined)).toBeUndefined()
  })

  it('matches the field by its full key, not a prefix', () => {
    expect(withFieldClause('d_bg:1<<2', 'd_b', '3<<4')).toBe('d_bg:1<<2;d_b:3<<4')
  })
})
