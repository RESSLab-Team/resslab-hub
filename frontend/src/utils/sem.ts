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

export const SEM_MAGNIFICATIONS = [250, 500, 2000] as const
export type SemMagnification = (typeof SEM_MAGNIFICATIONS)[number]

const BASE = import.meta.env.VITE_SEM_CDN_BASE_URL

export function semGlobalImageUrl(id: string): string {
  return `${BASE}/${id}/global.webp`
}

export function semLocalImageUrl(
  id: string,
  location: SemLocation,
  magnification: SemMagnification
): string {
  return `${BASE}/${id}/${location}_${magnification}.webp`
}

export function semDimplesUrl(
  id: string,
  location?: SemLocation,
  magnification?: SemMagnification
): string {
  if (location && magnification) {
    return `${BASE}/${id}/dimples_${location}_${magnification}.json`
  }
  return `${BASE}/${id}/dimples_all.json`
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

export function hotspotsFor(specimenType: string): Record<string, HotspotPosition> {
  if (specimenType === 'CNT') return CNT_HOTSPOTS
  // GP layout is not yet defined; render no hotspots until a real GP specimen lands.
  return {}
}
