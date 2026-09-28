/**
 * Run a task once the main thread has nothing better to do.
 *
 * For work that must happen soon but not *now*: the filter-rail profile after
 * a dashboard load, for instance, which used to sit between the data landing
 * and the table showing its rows (#354). `requestIdleCallback` fires once the
 * pending paints and event handlers are done; the timeout is the promise that
 * a busy page still runs the task within that many milliseconds.
 *
 * Browsers without `requestIdleCallback` (Safari before 18, jsdom) get a plain
 * macrotask, which at least lets the current flush paint first.
 *
 * Returns a function that cancels the task if it has not started yet.
 */
export function whenIdle(task: () => void, timeout = 1500): () => void {
  if (typeof requestIdleCallback === 'function') {
    const handle = requestIdleCallback(() => task(), { timeout })
    return () => cancelIdleCallback(handle)
  }
  const handle = setTimeout(task, 0)
  return () => clearTimeout(handle)
}
