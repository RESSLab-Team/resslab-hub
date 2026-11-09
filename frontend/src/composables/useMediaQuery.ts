import { onBeforeUnmount, onMounted, ref, type Ref } from 'vue'

/**
 * Whether a CSS media query matches, kept up to date while the component
 * lives. Without `window.matchMedia` (jsdom in the tests) it stays false.
 */
export function useMediaQuery(query: string): Ref<boolean> {
  const list = typeof window.matchMedia === 'function' ? window.matchMedia(query) : undefined
  const matches = ref(list?.matches ?? false)
  const onChange = (event: MediaQueryListEvent): void => {
    matches.value = event.matches
  }
  onMounted(() => list?.addEventListener?.('change', onChange))
  onBeforeUnmount(() => list?.removeEventListener?.('change', onChange))
  return matches
}
