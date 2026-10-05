import {
  SITES_HIT_LAYER,
  SITES_SOURCE,
  buildMapStyle,
  clusterProperties,
  graticule,
  sitesSource
} from '@/utils/mapStyle'
import { describe, expect, it } from 'vitest'

describe('mapStyle.buildMapStyle', () => {
  const style = buildMapStyle()

  it('has unique layer ids and every layer reads an existing source', () => {
    const ids = style.layers.map((layer) => layer.id)
    expect(new Set(ids).size).toBe(ids.length)
    for (const layer of style.layers) {
      if ('source' in layer && typeof layer.source === 'string') {
        expect(Object.keys(style.sources)).toContain(layer.source)
      }
    }
  })

  it('uses OpenFreeMap, with an attribution', () => {
    const omt = style.sources.omt
    expect(omt.type).toBe('vector')
    expect('url' in omt && omt.url).toMatch(/^https:\/\/tiles\.openfreemap\.org\//)
    expect('attribution' in omt && omt.attribution).toContain('OpenStreetMap')
    expect(style.glyphs).toMatch(/^https:\/\/tiles\.openfreemap\.org\/fonts\//)
  })
})

describe('mapStyle.graticule', () => {
  it('draws lines every 30 degrees', () => {
    const { features } = graticule()
    expect(features).toHaveLength(13 + 5)
    for (const feature of features) {
      const [[lng0, lat0], [lng1, lat1]] = feature.geometry.coordinates
      const fixed = lng0 === lng1 ? lng0 : lat0
      expect(lng0 === lng1 || lat0 === lat1).toBe(true)
      expect(Math.abs(fixed % 30)).toBe(0)
    }
  })
})

describe('mapStyle.sitesSource', () => {
  it('sums every category over a cluster', () => {
    const props = clusterProperties()
    expect(Object.keys(props)).toEqual(['t0', 't1', 't2', 't3', 't4', 't5', 't6', 't7', 't8'])
    expect(props.t3).toEqual(['+', ['get', 't3']])
  })

  it('clusters wider in the compact variant', () => {
    const data = { type: 'FeatureCollection' as const, features: [] }
    expect(sitesSource(data, false)).toMatchObject({ cluster: true, clusterRadius: 56 })
    expect(sitesSource(data, true).clusterRadius).toBe(76)
  })

  it('keeps the sites source alive with an invisible layer', () => {
    expect(SITES_HIT_LAYER).toMatchObject({ type: 'circle', source: SITES_SOURCE })
  })
})
