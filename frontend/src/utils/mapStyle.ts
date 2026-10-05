/**
 * The overview map's basemap and its sites source. The basemap is a flat
 * light grey world with white water, from OpenFreeMap vector tiles (no key,
 * no account). This is the one file allowed to hold basemap colours: a
 * MapLibre style is JSON read by WebGL, it cannot use a CSS var(). The
 * basemap stays light in dark mode on purpose, like a printed map.
 */
import type {
  GeoJSONSourceSpecification,
  LayerSpecification,
  LngLatBoundsLike,
  StyleSpecification
} from 'maplibre-gl'
import { MAP_CATEGORIES } from '@/utils/mapCategories'
import type { SiteCollection } from '@/utils/mapSites'

// OpenFreeMap has no SLA. If it goes away, these two URLs are what to change.
export const TILES_URL = 'https://tiles.openfreemap.org/planet'
export const GLYPHS_URL = 'https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf'
export const ATTRIBUTION =
  '<a href="https://openfreemap.org" target="_blank" rel="noreferrer">OpenFreeMap</a> ' +
  '<a href="https://www.openmaptiles.org/" target="_blank" rel="noreferrer">© OpenMapTiles</a> ' +
  '<a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">© OpenStreetMap contributors</a>'

const LAND = '#f0f0f0'
const WATER = '#ffffff'
const GRATICULE = '#e6e6e6'
const COUNTRY_LABEL = '#9b9b9b'
const CITY_LABEL = '#707070'

/** What "reset view" frames: every lab in the data, without the poles. */
export const WORLD_BOUNDS: LngLatBoundsLike = [
  [-128, -46],
  [178, 62]
]

export const SITES_SOURCE = 'sites'
export const CLUSTER_RADIUS = 56
export const CLUSTER_MAX_ZOOM = 10

// Local GeoJSON types: @types/geojson is not a direct dependency (see mapSites.ts).
interface LineFeature {
  type: 'Feature'
  properties: Record<string, never>
  geometry: { type: 'LineString'; coordinates: [number, number][] }
}

export interface LineCollection {
  type: 'FeatureCollection'
  features: LineFeature[]
}

/** Meridians and parallels every 30 degrees, as GeoJSON lines. */
export function graticule(): LineCollection {
  const features: LineFeature[] = []
  const line = (coordinates: [number, number][]) =>
    features.push({
      type: 'Feature',
      properties: {},
      geometry: { type: 'LineString', coordinates }
    })
  for (let lng = -180; lng <= 180; lng += 30) {
    line([
      [lng, -80],
      [lng, 84]
    ])
  }
  for (let lat = -60; lat <= 60; lat += 30) {
    line([
      [-180, lat],
      [180, lat]
    ])
  }
  return { type: 'FeatureCollection', features }
}

export function buildMapStyle(): StyleSpecification {
  const layers: LayerSpecification[] = [
    { id: 'bg', type: 'background', paint: { 'background-color': LAND } },
    {
      id: 'water',
      type: 'fill',
      source: 'omt',
      'source-layer': 'water',
      paint: { 'fill-color': WATER }
    },
    {
      id: 'grat',
      type: 'line',
      source: 'grat',
      paint: { 'line-color': GRATICULE, 'line-width': 0.6 }
    },
    {
      id: 'road',
      type: 'line',
      source: 'omt',
      'source-layer': 'transportation',
      minzoom: 5,
      filter: ['in', ['get', 'class'], ['literal', ['motorway', 'trunk']]],
      paint: { 'line-color': WATER, 'line-width': 0.7 }
    },
    {
      id: 'bnd',
      type: 'line',
      source: 'omt',
      'source-layer': 'boundary',
      filter: ['all', ['==', ['get', 'admin_level'], 2], ['!=', ['get', 'maritime'], 1]],
      paint: { 'line-color': WATER, 'line-width': 1 }
    },
    {
      id: 'country',
      type: 'symbol',
      source: 'omt',
      'source-layer': 'place',
      minzoom: 1.6,
      filter: ['==', ['get', 'class'], 'country'],
      layout: {
        'text-field': ['coalesce', ['get', 'name:en'], ['get', 'name']],
        'text-font': ['Noto Sans Regular'],
        'text-size': ['interpolate', ['linear'], ['zoom'], 2, 8.5, 5, 11],
        'text-transform': 'uppercase',
        'text-letter-spacing': 0.16,
        'text-max-width': 7
      },
      paint: { 'text-color': COUNTRY_LABEL, 'text-halo-color': LAND, 'text-halo-width': 1.2 }
    },
    {
      id: 'city',
      type: 'symbol',
      source: 'omt',
      'source-layer': 'place',
      minzoom: 5,
      filter: ['==', ['get', 'class'], 'city'],
      layout: {
        'text-field': ['coalesce', ['get', 'name:en'], ['get', 'name']],
        'text-font': ['Noto Sans Regular'],
        'text-size': 10,
        'text-letter-spacing': 0.04
      },
      paint: { 'text-color': CITY_LABEL, 'text-halo-color': LAND, 'text-halo-width': 1.4 }
    }
  ]
  return {
    version: 8,
    glyphs: GLYPHS_URL,
    sources: {
      omt: { type: 'vector', url: TILES_URL, attribution: ATTRIBUTION },
      grat: { type: 'geojson', data: graticule() }
    },
    layers
  }
}

/** Each cluster carries the sum of every `t<i>`, so its glyph can show the mix. */
export function clusterProperties(): Record<string, unknown> {
  return Object.fromEntries(MAP_CATEGORIES.map((_, i) => [`t${i}`, ['+', ['get', `t${i}`]]]))
}

/** Compact frames cluster a bit more: the glyphs are smaller but the screen is too. */
export function sitesSource(data: SiteCollection, compact: boolean): GeoJSONSourceSpecification {
  return {
    type: 'geojson',
    data,
    cluster: true,
    clusterRadius: Math.round(CLUSTER_RADIUS * (compact ? 1.35 : 1)),
    clusterMaxZoom: CLUSTER_MAX_ZOOM,
    clusterProperties: clusterProperties()
  }
}

// The markers are DOM, drawn from querySourceFeatures. MapLibre only loads
// the tiles of a source that some layer uses, so this invisible layer keeps
// the sites source alive.
export const SITES_HIT_LAYER: LayerSpecification = {
  id: 'sites-hit',
  type: 'circle',
  source: SITES_SOURCE,
  paint: { 'circle-radius': 1, 'circle-opacity': 0 }
}
