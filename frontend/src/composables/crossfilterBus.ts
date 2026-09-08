/**
 * Crossfilter bus — a plain, **non-reactive** pub/sub that drives the charts
 * during a brush drag *without touching Vue's reactivity*.
 *
 * THE PROBLEM
 * -----------
 * A brush drag cross-filters the whole dashboard. Routed through Vue (mutate the
 * `query` ref → recompute → re-render every chart *and the table*), every
 * pointermove collapses into a `flushJobs` long task. The table (≈100 fields per
 * row) is the heaviest thing in it, yet nobody is looking at the table mid-drag.
 *
 * THE MODEL (what the user asked for)
 * -----------------------------------
 *   · DURING the drag  → publish the live query here. Charts recompute their own
 *     aggregates from the in-memory dataset and repaint imperatively. Vue's
 *     `query` ref is NOT touched, so the table / URL sync / everything reactive
 *     stays put. Zero `flushJobs`.
 *   · ON pointer-up     → the dragged chart commits once through the normal Vue
 *     path (`change:searches` → `query`), and `publishSettle()` unfreezes the
 *     charts. Now reactivity updates the table and the rest — exactly once.
 *
 * This module deliberately uses no `ref`/`computed`/`watch`: subscribers are
 * called back directly, off the scheduler. Live publishes are coalesced to one
 * per animation frame (latest-wins); settle flushes any pending live frame first
 * so the last drag position is never dropped.
 *
 * LIFECYCLE (one drag gesture)
 * ----------------------------
 *   idle ──pointer-down──▶ dragging ──pointer-up──▶ settled (= idle)
 *
 *   1. Pointer-down on a brush sets `isBrushDragging` (interactionState.ts).
 *   2. Each drag frame the brush's host chart calls `publishLive(query)`;
 *      subscribers get `onLive` once per rAF and repaint imperatively.
 *   3. Pointer-up (DistributionBrush emits `dragend`): the host chart FIRST
 *      commits the final range through Vue (`change:searches`) and THEN calls
 *      `publishSettle()`. That order matters — the commit's reactive recompute
 *      flushes after settle (microtask), so it lands with charts unfrozen and
 *      becomes the reconciling render. `dragend` fires even for a no-op click,
 *      so subscribers can never get stuck frozen.
 */
import { perfMark, perfMeasure } from '@/utils/perf'

export interface CrossfilterListener {
  /** A live drag frame: the full query string as it stands mid-drag. */
  onLive: (query: string | undefined) => void
  /** The drag ended: stop freezing, fall back to the committed/reactive state. */
  onSettle: () => void
}

const listeners = new Set<CrossfilterListener>()

let frameHandle = 0
let pendingQuery: string | undefined
let hasPending = false

function flushLive(): void {
  frameHandle = 0
  if (!hasPending) return
  hasPending = false
  const query = pendingQuery
  // Benchmark (#354): the cost of one drag frame, every subscribed chart
  // included. Over ~16 ms here and the drag drops frames.
  perfMark('brush:live:start')
  for (const listener of listeners) listener.onLive(query)
  perfMark('brush:live:end', { charts: listeners.size })
  perfMeasure('brush:live', 'brush:live:start', 'brush:live:end')
}

/** Subscribe a chart to live/settle frames. Returns an unsubscribe fn. */
export function subscribeCrossfilter(listener: CrossfilterListener): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

/** Publish the live query for the current drag frame (coalesced per rAF). */
export function publishLive(query: string | undefined): void {
  if (listeners.size === 0) return // nobody to paint — don't schedule rAFs
  pendingQuery = query
  hasPending = true
  if (frameHandle) return
  if (typeof requestAnimationFrame === 'undefined') {
    // SSR / test fallback: fire synchronously.
    flushLive()
    return
  }
  frameHandle = requestAnimationFrame(flushLive)
}

/** End the drag: deliver any pending live frame, then notify settle. */
export function publishSettle(): void {
  if (frameHandle) {
    cancelAnimationFrame(frameHandle)
    flushLive()
  }
  for (const listener of listeners) listener.onSettle()
}
