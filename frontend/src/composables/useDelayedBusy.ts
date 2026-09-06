import { onScopeDispose, ref, watch, type Ref } from 'vue'

/** A wait shorter than this (a cache hit) shows nothing at all. */
export const SHOW_DELAY_MS = 150
/** Once shown, the indicator stays at least this long, so it never flickers. */
export const MIN_SHOWN_MS = 1000

/**
 * Turns a "busy" flag into a "show the indicator" flag that neither flashes
 * nor flickers: it goes true only when the wait outlives `showDelay`, and once
 * true it stays at least `minShown` even if the wait ended before that. A new
 * wait in the meantime cancels the pending hide.
 *
 * Same rules as the loading hairline of `SimpleTable`, which keeps its own
 * copy because it also has to ignore its local re-filters.
 */
export function useDelayedBusy(
  active: () => boolean,
  { showDelay = SHOW_DELAY_MS, minShown = MIN_SHOWN_MS } = {}
): Ref<boolean> {
  const shown = ref(false)
  let shownAt = 0
  let showTimer: ReturnType<typeof setTimeout> | undefined
  let hideTimer: ReturnType<typeof setTimeout> | undefined

  watch(
    active,
    (busy) => {
      if (busy) {
        if (hideTimer) {
          clearTimeout(hideTimer)
          hideTimer = undefined
        }
        if (!shown.value && !showTimer) {
          showTimer = setTimeout(() => {
            showTimer = undefined
            shown.value = true
            shownAt = Date.now()
          }, showDelay)
        }
        return
      }
      // The wait ended before the indicator appeared: never show it.
      if (showTimer) {
        clearTimeout(showTimer)
        showTimer = undefined
      }
      if (!shown.value) return
      const remaining = minShown - (Date.now() - shownAt)
      if (remaining <= 0) {
        shown.value = false
        return
      }
      hideTimer = setTimeout(() => {
        shown.value = false
        hideTimer = undefined
      }, remaining)
    },
    { immediate: true }
  )

  onScopeDispose(() => {
    clearTimeout(showTimer)
    clearTimeout(hideTimer)
  })

  return shown
}
