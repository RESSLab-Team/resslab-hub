import { useEscapeKey } from '@/composables/useEscapeKey'
import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { defineComponent, nextTick, ref, type Ref } from 'vue'

function mountWith(active: Ref<boolean>, onEscape: () => void) {
  return mount(
    defineComponent({
      setup: () => useEscapeKey(active, onEscape),
      template: '<div />'
    })
  )
}

function press(key: string): void {
  window.dispatchEvent(new KeyboardEvent('keydown', { key }))
}

describe('useEscapeKey', () => {
  it('calls back on Escape only while active, and stops after unmount', async () => {
    const active = ref(false)
    const onEscape = vi.fn()
    const wrapper = mountWith(active, onEscape)

    press('Escape')
    expect(onEscape).not.toHaveBeenCalled()

    active.value = true
    await nextTick()
    press('Enter')
    press('Escape')
    expect(onEscape).toHaveBeenCalledTimes(1)

    wrapper.unmount()
    press('Escape')
    expect(onEscape).toHaveBeenCalledTimes(1)
  })

  it('leaves Escape to an open dialog on top', async () => {
    const onEscape = vi.fn()
    const wrapper = mountWith(ref(true), onEscape)
    const dialog = document.createElement('div')
    dialog.className = 'v-overlay v-dialog v-overlay--active'
    document.body.appendChild(dialog)
    press('Escape')
    expect(onEscape).not.toHaveBeenCalled()

    dialog.remove()
    press('Escape')
    expect(onEscape).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })
})
