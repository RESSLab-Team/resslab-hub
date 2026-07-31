import { onScopeDispose, ref, watch, type Ref } from 'vue'

/**
 * Mirrors a numeric source, tweening between values instead of jumping — used
 * by the home KPIs so a live number that differs from the seeded snapshot
 * counts up (or down) into place. Nullish values pass through untouched, and
 * reduced-motion users get the jump.
 */
export function useCountUp(
  source: () => number | null | undefined,
  duration = 800
): Ref<number | null | undefined> {
  const display = ref(source())
  let frame = 0

  watch(source, (to) => {
    cancelAnimationFrame(frame)
    const from = display.value
    if (to == null || from == null || to === from) {
      display.value = to
      return
    }
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      display.value = to
      return
    }
    const start = performance.now()
    const step = (now: number): void => {
      const progress = Math.min((now - start) / duration, 1)
      const eased = 1 - (1 - progress) ** 3
      display.value = Math.round(from + (to - from) * eased)
      if (progress < 1) {
        frame = requestAnimationFrame(step)
      }
    }
    frame = requestAnimationFrame(step)
  })

  onScopeDispose(() => cancelAnimationFrame(frame))

  return display
}
