import { useEscapeKey } from '@/composables/useEscapeKey'
import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { defineComponent, nextTick, ref } from 'vue'

function press(key: string): void {
  window.dispatchEvent(new KeyboardEvent('keydown', { key }))
}

describe('useEscapeKey', () => {
  it('calls back on Escape only while active, and stops after unmount', async () => {
    const active = ref(false)
    const onEscape = vi.fn()
    const wrapper = mount(
      defineComponent({
        setup: () => useEscapeKey(active, onEscape),
        template: '<div />'
      })
    )

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
})
