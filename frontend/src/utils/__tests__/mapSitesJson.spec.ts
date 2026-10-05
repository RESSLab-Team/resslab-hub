import siteNames from '@/assets/map-sites.json'
import { describe, expect, it } from 'vitest'

// The keys are the backend's `sid` (utils/map_sites.py site_key): lat,lng with
// 2 decimals, never "-0.00". A key in another format would never match a site.
describe('assets/map-sites.json', () => {
  const entries = Object.entries(siteNames as Record<string, Record<string, string>>)

  it('is keyed like the backend site id', () => {
    expect(entries.length).toBeGreaterThan(0)
    for (const [sid] of entries) {
      expect(sid).toMatch(/^-?\d{1,2}\.\d{2},-?\d{1,3}\.\d{2}$/)
      expect(sid).not.toMatch(/-0\.00/)
    }
  })

  it('names the institution, the city and a 2-letter country code', () => {
    for (const [, name] of entries) {
      expect(Object.keys(name).sort()).toEqual(['cc', 'city', 'inst'])
      expect(name.inst.trim()).not.toBe('')
      expect(name.city.trim()).not.toBe('')
      expect(name.cc).toMatch(/^[A-Z]{2}$/)
    }
  })
})
