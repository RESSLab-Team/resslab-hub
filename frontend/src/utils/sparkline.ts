/**
 * Minimal sparkline: turn two numeric series into an SVG polyline.
 *
 * Used to preview an attached measured response (force–displacement,
 * stress–strain, …) inside an experiment card without pulling in a chart
 * library. `x` and `y` are the file's first two declared columns, already
 * parsed by `checkTimeSeriesFile`.
 */

export interface Sparkline {
  /** `points` attribute for an SVG <polyline>, in the given viewport. */
  points: string
  width: number
  height: number
}

export function sparkline(
  x: number[],
  y: number[],
  width = 132,
  height = 40,
  pad = 3
): Sparkline | null {
  const count = Math.min(x.length, y.length)
  if (count < 2) return null

  let minX = Infinity
  let maxX = -Infinity
  let minY = Infinity
  let maxY = -Infinity
  for (let index = 0; index < count; index++) {
    if (x[index] < minX) minX = x[index]
    if (x[index] > maxX) maxX = x[index]
    if (y[index] < minY) minY = y[index]
    if (y[index] > maxY) maxY = y[index]
  }
  const spanX = maxX - minX || 1
  const spanY = maxY - minY || 1
  const w = width - pad * 2
  const h = height - pad * 2

  const points: string[] = []
  for (let index = 0; index < count; index++) {
    const px = pad + ((x[index] - minX) / spanX) * w
    // SVG y grows downward, so flip.
    const py = pad + h - ((y[index] - minY) / spanY) * h
    points.push(`${px.toFixed(1)},${py.toFixed(1)}`)
  }

  return { points: points.join(' '), width, height }
}
