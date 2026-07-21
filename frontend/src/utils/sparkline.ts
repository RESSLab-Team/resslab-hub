/**
 * Minimal sparkline: turn a two-column time-series CSV into an SVG polyline.
 *
 * Used to preview an attached measured response (force–displacement,
 * stress–strain, …) inside an experiment card without pulling in a chart
 * library. The first numeric column is the x axis, the second the y axis.
 */

import { parseCsv } from '@/utils/csv'

export interface Sparkline {
  /** `points` attribute for an SVG <polyline>, in the given viewport. */
  points: string
  width: number
  height: number
}

export function sparkline(content: string, width = 132, height = 40, pad = 3): Sparkline | null {
  const rows = parseCsv(content)
  if (rows.length < 3) return null // header + at least two points

  const data: Array<[number, number]> = []
  for (const row of rows.slice(1)) {
    const x = Number(row[0])
    const y = Number(row[1])
    if (Number.isFinite(x) && Number.isFinite(y)) data.push([x, y])
  }
  if (data.length < 2) return null

  let minX = Infinity
  let maxX = -Infinity
  let minY = Infinity
  let maxY = -Infinity
  for (const [x, y] of data) {
    if (x < minX) minX = x
    if (x > maxX) maxX = x
    if (y < minY) minY = y
    if (y > maxY) maxY = y
  }
  const spanX = maxX - minX || 1
  const spanY = maxY - minY || 1
  const w = width - pad * 2
  const h = height - pad * 2

  const points = data
    .map(([x, y]) => {
      const px = pad + ((x - minX) / spanX) * w
      // SVG y grows downward, so flip.
      const py = pad + h - ((y - minY) / spanY) * h
      return `${px.toFixed(1)},${py.toFixed(1)}`
    })
    .join(' ')

  return { points, width, height }
}
