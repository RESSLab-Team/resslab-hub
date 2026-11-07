import { onBeforeUnmount, watch, type Ref } from 'vue'

/**
 * Call `onEscape` when the user presses Escape, but only while `active` is
 * true. Used by the drawers: the listener exists only while a drawer is open,
 * so a closed drawer never catches a key meant for something else.
 */
export function useEscapeKey(active: Ref<boolean>, onEscape: () => void): void {
  function onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Escape') onEscape()
  }
  watch(
    active,
    (on) => {
      if (on) window.addEventListener('keydown', onKeydown)
      else window.removeEventListener('keydown', onKeydown)
    },
    { immediate: true }
  )
  onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
}
