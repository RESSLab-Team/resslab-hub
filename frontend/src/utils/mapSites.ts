/**
 * Pure helpers on the GET /map/sites response: site names, the GeoJSON the
 * map clusters, totals, and the schematic of a program. No DOM, no maplibre.
 */
import type { MapCategory, MapProgram, MapSite } from '@/backend'
import siteNames from '@/assets/map-sites.json'
import {
  getBraceImage,
  getColumnMapImage,
  getConnectionSpecimenImage,
  getDuctileFractureImage,
  getDuctileFractureSpecimenImage,
  getEbfImage,
  getHSSColumnImage,
  getResidualStressImage,
  getSteelMaterialImage,
  getTensileCouponImage
} from '@/utils/component'
import { MAP_CATEGORIES, categoryIndex } from '@/utils/mapCategories'

export interface SiteName {
  inst: string
  city: string
  cc: string
}

export interface SiteLabel extends SiteName {
  /** false when the site is not in map-sites.json: `inst` is then its coordinates */
  known: boolean
}

// map-sites.json is keyed by the backend's `sid` (lat,lng rounded to 2
// decimals). A site that is not in it (a new lab after a data upload, or one
// we could not name for sure) shows its coordinates until someone adds it.
const NAMES = siteNames as Record<string, SiteName>

export function labelFor(site: Pick<MapSite, 'sid'>): SiteLabel {
  const name = NAMES[site.sid]
  if (name) return { ...name, known: true }
  return { inst: site.sid.replace(',', ', '), city: '', cc: '', known: false }
}

/** What the panel shows: a cluster (its member sites) or one site. */
export interface ClusterSelection {
  kind: 'cluster'
  /** marker key, c<cluster_id> */
  key: string
  sids: string[]
}

export interface SiteSelection {
  kind: 'site'
  /** marker key, s<sid> */
  key: string
  sid: string
  /** the cluster the site was opened from, for the back button */
  back: ClusterSelection | null
}

export type Selection = ClusterSelection | SiteSelection

export interface SiteProps {
  sid: string
  n: number
  /** `t<i>` = count of MAP_CATEGORIES[i], summed by the cluster source */
  [t: `t${number}`]: number
}

export interface SiteFeature {
  type: 'Feature'
  geometry: { type: 'Point'; coordinates: [number, number] }
  properties: SiteProps
}

export interface SiteCollection {
  type: 'FeatureCollection'
  features: SiteFeature[]
}

export type Counts = Partial<Record<MapCategory, number>>

/** The counts of a site without the hidden categories. */
export function visibleCounts(counts: Counts, hidden: ReadonlySet<MapCategory>): Counts {
  const out: Counts = {}
  for (const { id } of MAP_CATEGORIES) {
    const n = counts[id] ?? 0
    if (n > 0 && !hidden.has(id)) out[id] = n
  }
  return out
}

/** A count as the dashboards write it: 1’234. */
export function formatCount(n: number): string {
  return n.toLocaleString('en-CH')
}

/** 46.52 N · 6.57 E, 33.87 S · 151.21 E */
export function formatLatLng(lat: number, lng: number): string {
  const part = (v: number, pos: string, neg: string) =>
    `${Math.abs(v).toFixed(2)} ${v >= 0 ? pos : neg}`
  return `${part(lat, 'N', 'S')} · ${part(lng, 'E', 'W')}`
}

export function sumCounts(counts: Counts): number {
  return Object.values(counts).reduce((a, b) => a + (b ?? 0), 0)
}

/** One point per site, hidden categories zeroed, empty sites dropped. */
export function siteFeatures(
  sites: MapSite[],
  hidden: ReadonlySet<MapCategory> = new Set()
): SiteCollection {
  const features: SiteFeature[] = []
  for (const site of sites) {
    const counts = visibleCounts(site.counts as Counts, hidden)
    const n = sumCounts(counts)
    if (n === 0) continue
    const properties: SiteProps = { sid: site.sid, n }
    MAP_CATEGORIES.forEach(({ id }, i) => {
      properties[`t${i}`] = counts[id] ?? 0
    })
    features.push({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [site.lng, site.lat] },
      properties
    })
  }
  return { type: 'FeatureCollection', features }
}

/** Back from the `t<i>` properties of a site or cluster feature to counts. */
export function countsOf(props: { readonly [t: `t${number}`]: unknown }): Counts {
  const out: Counts = {}
  MAP_CATEGORIES.forEach(({ id }, i) => {
    const n = Number(props[`t${i}`] ?? 0)
    if (n > 0) out[id] = n
  })
  return out
}

export interface Totals {
  sites: number
  tests: number
  /** per category, hidden ones included (the legend shows them greyed) */
  perCategory: Record<MapCategory, number>
}

export function totals(sites: MapSite[], hidden: ReadonlySet<MapCategory> = new Set()): Totals {
  const perCategory = Object.fromEntries(MAP_CATEGORIES.map(({ id }) => [id, 0])) as Record<
    MapCategory,
    number
  >
  let count = 0
  let tests = 0
  for (const site of sites) {
    let visible = 0
    for (const { id } of MAP_CATEGORIES) {
      const n = (site.counts as Counts)[id] ?? 0
      perCategory[id] += n
      if (!hidden.has(id)) visible += n
    }
    if (visible > 0) {
      count += 1
      tests += visible
    }
  }
  return { sites: count, tests, perCategory }
}

export interface MixItem {
  id: MapCategory
  n: number
  /** 0..1 of the total */
  share: number
}

/** Categories of some counts, biggest first (ties in MAP_CATEGORIES order). */
export function mixOf(counts: Counts): MixItem[] {
  const total = sumCounts(counts)
  return MAP_CATEGORIES.map(({ id }) => ({ id, n: counts[id] ?? 0 }))
    .filter((item) => item.n > 0)
    .sort((a, b) => b.n - a.n || categoryIndex(a.id) - categoryIndex(b.id))
    .map((item) => ({ ...item, share: total > 0 ? item.n / total : 0 }))
}

/** Every site of a set of sids, merged: what a cluster shows. */
export function mergedCounts(sites: MapSite[], hidden: ReadonlySet<MapCategory>): Counts {
  const out: Counts = {}
  for (const site of sites) {
    for (const [id, n] of Object.entries(visibleCounts(site.counts as Counts, hidden))) {
      out[id as MapCategory] = (out[id as MapCategory] ?? 0) + (n ?? 0)
    }
  }
  return out
}

export function visiblePrograms(site: MapSite, hidden: ReadonlySet<MapCategory>): MapProgram[] {
  return site.programs.filter((program) => !hidden.has(program.category))
}

/** The figure column as people read it (columns join two values with "|"). */
export function figureLabel(program: Pick<MapProgram, 'figure'>): string {
  return (program.figure ?? '')
    .split('|')
    .map((part) => part.trim())
    .filter(Boolean)
    .join(' · ')
}

/** The schematic of a program, or '' when there is none. */
export function programImage(program: Pick<MapProgram, 'category' | 'figure'>): string {
  const figure = program.figure ?? ''
  switch (program.category) {
    case 'braces':
      return getBraceImage(figure) ?? ''
    case 'columns': {
      const [axis = '', bc = ''] = figure.split('|')
      return getColumnMapImage(axis, bc) ?? ''
    }
    case 'connections':
      return getConnectionSpecimenImage(figure)
    case 'materials':
      return getSteelMaterialImage()
    case 'tensile-coupon':
      return getTensileCouponImage()
    case 'ductile-fracture':
      return getDuctileFractureSpecimenImage(figure) ?? getDuctileFractureImage()
    case 'residual-stress':
      return getResidualStressImage()
    // These two helpers warn on an unknown value, so skip the empty one.
    case 'hss-column':
      return figure ? getHSSColumnImage(figure) : ''
    case 'eccentric-braced-frame':
      return figure ? getEbfImage(figure) : ''
  }
}
