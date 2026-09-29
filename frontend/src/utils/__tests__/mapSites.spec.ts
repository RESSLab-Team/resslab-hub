import type { MapProgram, MapSite } from '@/backend'
import { MapCategory } from '@/backend'
import {
  countsOf,
  figureLabel,
  labelFor,
  mergedCounts,
  mixOf,
  programImage,
  siteFeatures,
  totals,
  visiblePrograms
} from '@/utils/mapSites'
import { describe, expect, it } from 'vitest'

const program = (category: MapCategory, n: number, figure?: string | null): MapProgram => ({
  category,
  program: `P ${category}`,
  year: 2010,
  n,
  first_id: 'X1',
  figure
})

const epfl: MapSite = {
  sid: '46.52,6.57',
  lat: 46.518,
  lng: 6.568,
  n: 12,
  counts: { braces: 2, materials: 10 },
  programs: [program(MapCategory.Materials, 10), program(MapCategory.Braces, 2, 'Gusset plate')]
}

const unknown: MapSite = {
  sid: '-12.34,56.78',
  lat: -12.34,
  lng: 56.78,
  n: 3,
  counts: { braces: 3 },
  programs: [program(MapCategory.Braces, 3)]
}

describe('mapSites.labelFor', () => {
  it('names a site from the lookup file', () => {
    expect(labelFor(epfl)).toEqual({ inst: 'EPFL', city: 'Lausanne', cc: 'CH', known: true })
  })

  it('shows the coordinates of a site that is not in the file', () => {
    expect(labelFor(unknown)).toEqual({ inst: '-12.34, 56.78', city: '', cc: '', known: false })
  })
})

describe('mapSites.siteFeatures', () => {
  it('builds one point per site, lng first, with t<i> per category', () => {
    const { features } = siteFeatures([epfl, unknown])
    expect(features).toHaveLength(2)
    expect(features[0].geometry.coordinates).toEqual([6.568, 46.518])
    expect(features[0].properties).toMatchObject({ sid: '46.52,6.57', n: 12, t0: 2, t1: 0, t3: 10 })
    expect(Object.keys(features[0].properties).filter((key) => key.startsWith('t'))).toHaveLength(9)
  })

  it('zeroes hidden categories, recomputes n and drops empty sites', () => {
    const { features } = siteFeatures([epfl, unknown], new Set([MapCategory.Braces]))
    expect(features).toHaveLength(1)
    expect(features[0].properties).toMatchObject({ sid: '46.52,6.57', n: 10, t0: 0, t3: 10 })
  })

  it('reads the counts back from the feature properties', () => {
    const { features } = siteFeatures([epfl])
    expect(countsOf(features[0].properties)).toEqual({ braces: 2, materials: 10 })
    expect(countsOf({ t0: 1, t8: '4' })).toEqual({ braces: 1, 'eccentric-braced-frame': 4 })
  })
})

describe('mapSites.totals', () => {
  it('counts sites and tests, every category in perCategory', () => {
    const all = totals([epfl, unknown])
    expect(all.sites).toBe(2)
    expect(all.tests).toBe(15)
    expect(all.perCategory.braces).toBe(5)
    expect(all.perCategory.materials).toBe(10)
    expect(all.perCategory['hss-column']).toBe(0)
  })

  it('leaves hidden categories out of sites and tests, not out of perCategory', () => {
    const some = totals([epfl, unknown], new Set([MapCategory.Braces]))
    expect(some.sites).toBe(1)
    expect(some.tests).toBe(10)
    expect(some.perCategory.braces).toBe(5)
  })
})

describe('mapSites.mixOf', () => {
  it('sorts biggest first, ties in category order, with shares', () => {
    expect(mixOf({ materials: 2, braces: 2, columns: 4 })).toEqual([
      { id: 'columns', n: 4, share: 0.5 },
      { id: 'braces', n: 2, share: 0.25 },
      { id: 'materials', n: 2, share: 0.25 }
    ])
    expect(mixOf({})).toEqual([])
  })

  it('merges the counts of several sites', () => {
    expect(mergedCounts([epfl, unknown], new Set())).toEqual({ braces: 5, materials: 10 })
    expect(mergedCounts([epfl, unknown], new Set([MapCategory.Materials]))).toEqual({ braces: 5 })
  })

  it('filters the programs of hidden categories', () => {
    const programs = visiblePrograms(epfl, new Set([MapCategory.Materials]))
    expect(programs.map((p) => p.category)).toEqual(['braces'])
  })
})

describe('mapSites.figureLabel', () => {
  it('joins the column figure parts', () => {
    expect(figureLabel({ figure: 'Strong|Fixed-Free' })).toBe('Strong · Fixed-Free')
    expect(figureLabel({ figure: 'Gusset plate' })).toBe('Gusset plate')
    expect(figureLabel({ figure: null })).toBe('')
  })
})

describe('mapSites.programImage', () => {
  it('picks the schematic of each category', () => {
    expect(programImage({ category: MapCategory.Braces, figure: 'Gusset plate' })).toMatch(
      /img\/brace\/type\/gusset-plate\.png$/
    )
    expect(programImage({ category: MapCategory.Columns, figure: 'Weak|Fixed-Free' })).toMatch(
      /Fixed_Free_WeakAxis\.png$/
    )
    expect(programImage({ category: MapCategory.DuctileFracture, figure: 'GP' })).toMatch(
      /ductile-fracture\/gp\.png$/
    )
    expect(programImage({ category: MapCategory.HssColumn, figure: 'CF' })).toMatch(
      /cantilever\.jpg$/
    )
    expect(programImage({ category: MapCategory.EccentricBracedFrame, figure: 'TF1' })).toMatch(
      /EBF_1\.png$/
    )
  })

  it('returns an empty string when there is no schematic', () => {
    expect(programImage({ category: MapCategory.Braces, figure: null })).toBe('')
    expect(programImage({ category: MapCategory.HssColumn, figure: null })).toBe('')
    expect(programImage({ category: MapCategory.EccentricBracedFrame, figure: '' })).toBe('')
  })

  it('falls back to the generic ductile fracture image', () => {
    expect(programImage({ category: MapCategory.DuctileFracture, figure: null })).not.toBe('')
  })
})
