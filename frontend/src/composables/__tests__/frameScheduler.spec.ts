import { cancelScheduled, scheduleFrameUpdate } from '@/composables/frameScheduler'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// Deterministic rAF (same technique as crossfilterBus.spec): capture callbacks
// and flush them on demand so the per-frame batching can be asserted.
let rafCallbacks: Map<number, FrameRequestCallback>
let rafSeq: number

function flushFrame(): void {
  const callbacks = [...rafCallbacks.values()]
  rafCallbacks.clear()
  for (const callback of callbacks) callback(0)
}

beforeEach(() => {
  rafCallbacks = new Map()
  rafSeq = 0
  vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
    rafCallbacks.set(++rafSeq, callback)
    return rafSeq
  })
})
afterEach(() => {
  // Drain anything a test left queued so module state can't leak across tests.
  while (rafCallbacks.size > 0) flushFrame()
  vi.unstubAllGlobals()
})

describe('frameScheduler', () => {
  it('spreads tasks across frames, BATCH_PER_FRAME at a time', () => {
    const ran: string[] = []
    scheduleFrameUpdate('a', () => ran.push('a'))
    scheduleFrameUpdate('b', () => ran.push('b'))
    scheduleFrameUpdate('c', () => ran.push('c'))
    scheduleFrameUpdate('d', () => ran.push('d'))
    expect(ran).toEqual([])
    flushFrame()
    expect(ran).toEqual(['a', 'b', 'c']) // BATCH_PER_FRAME (3) per frame
    flushFrame()
    expect(ran).toEqual(['a', 'b', 'c', 'd'])
  })

  it('coalesces per key, latest task wins', () => {
    const ran: string[] = []
    scheduleFrameUpdate('key', () => ran.push('stale'))
    scheduleFrameUpdate('key', () => ran.push('fresh'))
    flushFrame()
    expect(ran).toEqual(['fresh'])
  })

  it('cancelScheduled drops a queued task', () => {
    const ran: string[] = []
    scheduleFrameUpdate('doomed', () => ran.push('doomed'))
    scheduleFrameUpdate('kept', () => ran.push('kept'))
    cancelScheduled('doomed')
    flushFrame()
    expect(ran).toEqual(['kept'])
  })

  it('cancelScheduled is a no-op for unknown keys', () => {
    expect(() => cancelScheduled('never-scheduled')).not.toThrow()
  })
})
