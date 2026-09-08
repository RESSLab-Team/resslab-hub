import { whenIdle } from '@/utils/idle'
import { afterEach, describe, expect, it, vi } from 'vitest'

describe('whenIdle', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  it('uses requestIdleCallback with a timeout when the browser has it', () => {
    const request = vi.fn(() => 7)
    const cancel = vi.fn()
    vi.stubGlobal('requestIdleCallback', request)
    vi.stubGlobal('cancelIdleCallback', cancel)
    const task = vi.fn()

    const stop = whenIdle(task, 500)
    expect(request).toHaveBeenCalledWith(expect.any(Function), { timeout: 500 })
    stop()
    expect(cancel).toHaveBeenCalledWith(7)

    vi.unstubAllGlobals()
  })

  it('falls back to a macrotask elsewhere, still cancellable', () => {
    vi.useFakeTimers()
    const ran = vi.fn()
    const dropped = vi.fn()
    whenIdle(ran)
    const stop = whenIdle(dropped)
    stop()
    vi.runAllTimers()
    expect(ran).toHaveBeenCalledOnce()
    expect(dropped).not.toHaveBeenCalled()
  })
})
