/**
 * Spread a burst of reactive updates across animation frames.
 *
 * When a dashboard filters locally, every chart + the table recompute at once.
 * Setting all their refs in the same microtask collapses into a single
 * `flushJobs` long task (Vue reconciliation + ECharts `setOption` back to back).
 * Routing each ref-write through this scheduler moves it into its own frame
 * slot, so the browser paints — and stays responsive — between updates instead
 * of freezing for one long task.
 *
 * Coalescing is per key and latest-wins: if a new update for a key is scheduled
 * before its queued one has run, the queued task is replaced rather than
 * appended. A fast slider drag therefore never backs up an unbounded queue — it
 * always renders the newest value for each chart.
 */

// A few updates per frame: each chart write is only a few ms, so a small batch
// keeps every frame within budget while letting the whole dashboard settle in a
// handful of frames rather than one long task.
const BATCH_PER_FRAME = 2

const pending = new Map<string, () => void>()
const queue: string[] = []
let scheduled = false

function drain(): void {
  for (let i = 0; i < BATCH_PER_FRAME; i++) {
    const key = queue.shift()
    if (key === undefined) break
    const task = pending.get(key)
    pending.delete(key)
    task?.()
  }
  if (queue.length > 0) {
    requestAnimationFrame(drain)
  } else {
    scheduled = false
  }
}

/** Drop a queued update (call on unmount so a task never runs against dead refs). */
export function cancelScheduled(key: string): void {
  if (!pending.delete(key)) return
  const index = queue.indexOf(key)
  if (index !== -1) queue.splice(index, 1)
}

export function scheduleFrameUpdate(key: string, task: () => void): void {
  // Non-DOM environments (unit tests, SSR) have no rAF — just run immediately.
  if (typeof requestAnimationFrame === 'undefined') {
    task()
    return
  }
  if (!pending.has(key)) queue.push(key)
  pending.set(key, task)
  if (!scheduled) {
    scheduled = true
    requestAnimationFrame(drain)
  }
}
