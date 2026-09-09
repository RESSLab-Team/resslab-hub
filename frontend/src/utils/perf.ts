/**
 * Timing marks for the dashboard benchmark (#354).
 *
 * The exploration engine keeps every row in memory and does the filtering,
 * counting and sorting in the browser, so a slow dashboard is a browser
 * problem and the Performance panel is where you see it. What the panel does
 * *not* show is which of our own phases a long task belongs to — the fetch,
 * the one-off filter-rail profile, an ECharts repaint, a table window. These
 * marks name them, and `scripts/bench-dashboard.mjs` reads them back.
 *
 * They stay on in production. A `performance.mark` is a few microseconds and
 * writes to a buffer nobody reads unless they open the panel, where the names
 * show up on their own row and make a profile readable at a glance.
 *
 * Every name starts with `rh:` so the harness can pick ours out of the buffer.
 */

/** Prefix of every mark and measure this module writes. */
export const PERF_PREFIX = 'rh:'

// jsdom (vitest) has no User Timing API, and neither do very old browsers.
// Resolved once: this is called on every chart repaint, including drag frames.
const supported = typeof performance !== 'undefined' && typeof performance.mark === 'function'

/**
 * Write a point in time.
 *
 * `detail` rides along on the entry (rows, field count, live or not) so the
 * harness gets the number without a second lookup. It is dropped silently by
 * browsers that only accept the one-argument form.
 */
export function perfMark(name: string, detail?: unknown): void {
  if (!supported) return
  try {
    performance.mark(PERF_PREFIX + name, detail === undefined ? undefined : { detail })
  } catch {
    // A full buffer or a structured-clone failure on `detail` must never take
    // the dashboard down with it: a missing measurement is not a bug worth
    // showing a user.
  }
}

/**
 * Measure between two marks written by {@link perfMark}.
 *
 * `end` defaults to now. A missing start mark throws in the browser, so the
 * whole call is guarded: a measure is a nice-to-have, never a dependency.
 */
export function perfMeasure(name: string, start: string, end?: string): void {
  if (!supported || typeof performance.measure !== 'function') return
  try {
    performance.measure(
      PERF_PREFIX + name,
      end === undefined
        ? { start: PERF_PREFIX + start }
        : { start: PERF_PREFIX + start, end: PERF_PREFIX + end }
    )
  } catch {
    // Same reason as above.
  }
}
