/**
 * Fixed-height row windowing for the light-DOM table body.
 *
 * The table renders plain `<tr>`/`<td>` (no per-row Vuetify components), so a
 * keyed patch of the *visible* rows is only a few ms — cheap enough to re-run
 * every animation frame while a brush drag cross-filters the dataset. This
 * composable keeps the mounted-row set bounded: it tracks the scroll position
 * and viewport height and exposes the slice `[startIndex, endIndex)` to render,
 * plus spacer heights so the scrollbar still reflects the full page.
 *
 * Below `DISABLE_BELOW` rows we render everything (no window): the common
 * 5/10/20 page sizes never scroll, so windowing would only add scroll-sync
 * bookkeeping for no benefit. Virtualization engages only for the large
 * (100/1000) page sizes.
 *
 * The window math lives in the pure `computeWindow` helper so it can be unit
 * tested without a DOM.
 */
import { computed, onBeforeUnmount, onMounted, ref, watch, type Ref } from 'vue'

/** Row height in px — must match the compact-density row height in the table CSS. */
export const ROW_HEIGHT = 38
/** Extra rows rendered above/below the viewport to cover fast scrolls. */
export const OVERSCAN = 6
/** At or below this many rows, skip windowing and render the whole page. */
export const DISABLE_BELOW = 40

export interface RowWindow {
  startIndex: number
  endIndex: number
  padTop: number
  padBottom: number
}

/**
 * Pure window computation. Given the scroll offset, viewport height and total
 * row count, return the row slice to mount and the spacer heights around it.
 */
export function computeWindow(
  scrollTop: number,
  viewportHeight: number,
  total: number,
  rowHeight = ROW_HEIGHT,
  overscan = OVERSCAN,
  disableBelow = DISABLE_BELOW
): RowWindow {
  if (total <= disableBelow || viewportHeight <= 0) {
    return { startIndex: 0, endIndex: total, padTop: 0, padBottom: 0 }
  }
  const first = Math.floor(scrollTop / rowHeight)
  const visibleCount = Math.ceil(viewportHeight / rowHeight)
  const startIndex = Math.max(0, first - overscan)
  const endIndex = Math.min(total, first + visibleCount + overscan)
  return {
    startIndex,
    endIndex,
    padTop: startIndex * rowHeight,
    padBottom: (total - endIndex) * rowHeight
  }
}

/**
 * Bind windowing to a scroll container and a reactive row count.
 *
 * @param scrollEl  the `overflow-y:auto` viewport element
 * @param total     reactive total row count of the current page
 */
export function useVirtualRows(scrollEl: Ref<HTMLElement | undefined>, total: Ref<number>) {
  const scrollTop = ref(0)
  const viewportHeight = ref(0)

  const rowWindow = computed<RowWindow>(() =>
    computeWindow(scrollTop.value, viewportHeight.value, total.value)
  )

  function onScroll(): void {
    if (scrollEl.value) scrollTop.value = scrollEl.value.scrollTop
  }

  let resizeObserver: ResizeObserver | undefined
  onMounted(() => {
    const el = scrollEl.value
    if (!el) return
    viewportHeight.value = el.clientHeight
    el.addEventListener('scroll', onScroll, { passive: true })
    if ('ResizeObserver' in window) {
      resizeObserver = new ResizeObserver(() => {
        viewportHeight.value = el.clientHeight
      })
      resizeObserver.observe(el)
    }
  })
  onBeforeUnmount(() => {
    scrollEl.value?.removeEventListener('scroll', onScroll)
    resizeObserver?.disconnect()
  })

  // When the page shrinks (filter narrows the result set), a stale scrollTop can
  // leave the viewport past the new content; clamp it so the window recomputes
  // from a valid offset.
  watch(total, (count) => {
    const maxScroll = Math.max(0, count * ROW_HEIGHT - viewportHeight.value)
    if (scrollEl.value && scrollEl.value.scrollTop > maxScroll) {
      scrollEl.value.scrollTop = maxScroll
      scrollTop.value = maxScroll
    }
  })

  return { window: rowWindow }
}
