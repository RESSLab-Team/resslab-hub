import { invertMapping } from '@/composables/chart'
import { describe, expect, it } from 'vitest'

describe('invertMapping', () => {
  it('turns a display label back into the raw value', () => {
    const inverse = invertMapping(
      new Map([
        ['False', 'Bare'],
        ['True', 'Composite']
      ])
    )
    expect(inverse.get('Composite')).toBe('True')
    expect(inverse.get('Bare')).toBe('False')
  })

  it('has no entry for an unmapped label, so the `?? label` fallback passes it through', () => {
    const inverse = invertMapping(new Map([['True', 'Composite']]))
    expect(inverse.get('RBS')).toBeUndefined()
    expect(inverse.get('RBS') ?? 'RBS').toBe('RBS')
  })

  it('is empty for an empty mapping', () => {
    expect(invertMapping(new Map()).size).toBe(0)
  })
})
