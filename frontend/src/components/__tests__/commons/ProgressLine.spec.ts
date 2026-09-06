import ProgressLine from '@/components/commons/ProgressLine.vue'
import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

describe('ProgressLine', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('shows the label at once and the bar only after the delay', async () => {
    const wrapper = mount(ProgressLine, { props: { active: true, label: 'Loading…' } })
    expect(wrapper.text()).toBe('Loading…')
    expect(wrapper.find('.progress-track').classes()).not.toContain('is-shown')

    vi.advanceTimersByTime(200)
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.progress-track').classes()).toContain('is-shown')
    expect(wrapper.find('.progress-track').classes()).toContain('is-marching')
  })

  it('never shows the bar for a wait shorter than the delay', async () => {
    const wrapper = mount(ProgressLine, { props: { active: true, label: 'Loading…' } })
    vi.advanceTimersByTime(50)
    await wrapper.setProps({ active: false })
    vi.advanceTimersByTime(500)
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.progress-line').exists()).toBe(false)
  })

  it('fills the bar from the count instead of marching', async () => {
    const wrapper = mount(ProgressLine, {
      props: { active: true, label: 'Loading 1 of 4 files…', done: 1, total: 4 }
    })
    vi.advanceTimersByTime(200)
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.progress-track').classes()).not.toContain('is-marching')
    expect(wrapper.find('.progress-fill').attributes('style')).toContain('width: 25%')

    await wrapper.setProps({ done: 4 })
    expect(wrapper.find('.progress-fill').attributes('style')).toContain('width: 100%')
  })

  it('renders nothing when not active', () => {
    const wrapper = mount(ProgressLine, { props: { active: false, label: 'x' } })
    expect(wrapper.find('.progress-line').exists()).toBe(false)
  })
})
