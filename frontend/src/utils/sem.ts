import axios from 'axios'

export type SemLocation = 'north' | 'south' | 'east' | 'west' | 'middle'

export interface HotspotPosition {
  x: number // percent of image width
  y: number // percent of image height
}

export const CNT_HOTSPOTS: Record<SemLocation, HotspotPosition> = {
  north: { x: 50, y: 15 },
  south: { x: 50, y: 75 },
  east: { x: 70, y: 45 },
  west: { x: 30, y: 45 },
  middle: { x: 50, y: 45 }
}

// GP coupons are imaged at three locations across the fracture surface. Positions
// are approximate (per the View Panel spec) and may be tuned against the real
// global image.
export const GP_HOTSPOTS: Partial<Record<SemLocation, HotspotPosition>> = {
  west: { x: 25, y: 50 },
  middle: { x: 50, y: 50 },
  east: { x: 75, y: 50 }
}

export const SEM_MAGNIFICATIONS = [250, 500, 2000] as const
export type SemMagnification = (typeof SEM_MAGNIFICATIONS)[number]

/**
 * Per-specimen SEM layout, precomputed alongside the WebP/dimple artifacts
 * (see backend/data/precompute_sem.py). ``surfaces`` is 1 for ordinary coupons
 * and 2 for ruptured bars imaged on both fracture surfaces (Ozden et al.).
 */
export interface SemManifest {
  surfaces: number
  locations: SemLocation[]
  magnifications: SemMagnification[]
}

const BASE = import.meta.env.VITE_SEM_CDN_BASE_URL

// Surface 1 lives at the specimen root; further surfaces under "s<n>/".
function surfacePrefix(surface?: number): string {
  return surface && surface > 1 ? `s${surface}/` : ''
}

export function semGlobalImageUrl(id: string, surface?: number): string {
  return `${BASE}/${id}/${surfacePrefix(surface)}global.webp`
}

export function semLocalImageUrl(
  id: string,
  location: SemLocation,
  magnification: SemMagnification,
  surface?: number
): string {
  return `${BASE}/${id}/${surfacePrefix(surface)}${location}_${magnification}.webp`
}

export function semDimplesUrl(
  id: string,
  location?: SemLocation,
  magnification?: SemMagnification,
  surface?: number
): string {
  const prefix = surfacePrefix(surface)
  if (location && magnification) {
    return `${BASE}/${id}/${prefix}dimples_${location}_${magnification}.json`
  }
  return `${BASE}/${id}/${prefix}dimples_all.json`
}

export function semManifestUrl(id: string): string {
  return `${BASE}/${id}/manifest.json`
}

export async function fetchSemManifest(id: string): Promise<SemManifest> {
  const { data } = await axios.get<SemManifest>(semManifestUrl(id))
  return data
}

export async function fetchDimples(url: string): Promise<number[]> {
  const { data } = await axios.get<number[]>(url)
  return data
}

/**
 * Build CDF series points from a list of diameters: each point is (diameter, rank/N).
 * Input may be unsorted; the result is sorted ascending by diameter.
 */
export function computeCdf(diameters: number[]): [number, number][] {
  const sorted = [...diameters].sort((a, b) => a - b)
  const n = sorted.length
  if (n === 0) return []
  return sorted.map((d, i) => [d, (i + 1) / n])
}

/**
 * Hotspot positions for a specimen type, optionally restricted to the locations
 * actually present (from the SEM manifest) so a specimen never shows a marker
 * with no image behind it.
 */
export function hotspotsFor(
  specimenType: string,
  locations?: SemLocation[]
): Record<string, HotspotPosition> {
  const base: Partial<Record<SemLocation, HotspotPosition>> =
    specimenType === 'GP' ? GP_HOTSPOTS : CNT_HOTSPOTS
  if (!locations) return base as Record<string, HotspotPosition>
  const allowed = new Set(locations)
  return Object.fromEntries(Object.entries(base).filter(([loc]) => allowed.has(loc as SemLocation)))
}
