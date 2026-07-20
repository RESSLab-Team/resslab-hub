import { publishLive, publishSettle, subscribeCrossfilter } from '@/composables/crossfilterBus'
import { useDataset } from '@/composables/useDataset'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// Deterministic rAF: capture callbacks and flush them on demand, so the bus's
// per-frame coalescing can be asserted without real frames.
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
  vi.stubGlobal('cancelAnimationFrame', (id: number) => rafCallbacks.delete(id))
})
afterEach(() => {
  vi.unstubAllGlobals()
})

function record() {
  const events: string[] = []
  const unsubscribe = subscribeCrossfilter({
    onLive: (query) => events.push(`live:${query}`),
    onSettle: () => events.push('settle')
  })
  return { events, unsubscribe }
}

describe('crossfilterBus', () => {
  it('coalesces publishes within one frame, latest wins', () => {
    const { events, unsubscribe } = record()
    publishLive('a:1')
    publishLive('a:2')
    expect(events).toEqual([]) // nothing until the frame fires
    flushFrame()
    expect(events).toEqual(['live:a:2'])
    unsubscribe()
  })

  it('settle delivers the pending live frame first, then onSettle', () => {
    const { events, unsubscribe } = record()
    publishLive('a:3')
    publishSettle()
    expect(events).toEqual(['live:a:3', 'settle'])
    unsubscribe()
  })

  it('stops delivering after unsubscribe', () => {
    const { events, unsubscribe } = record()
    unsubscribe()
    publishLive('a:4')
    flushFrame()
    publishSettle()
    expect(events).toEqual([])
  })

  it('does not schedule frames when nobody is subscribed', () => {
    publishLive('a:5')
    expect(rafCallbacks.size).toBe(0)
  })
})

// End-to-end slice of the drag pipeline: dataset → live query → sync counts →
// settle, exactly what a chart's bus subscription does.
describe('crossfilter drag integration', () => {
  it('recomputes live counts from the in-memory dataset per frame', async () => {
    const dataset = useDataset('bus-integration', async () => [
      { id: '1', type: 'A', value: 10 },
      { id: '2', type: 'B', value: 20 },
      { id: '3', type: 'A', value: 30 }
    ])
    await dataset.ready()

    const frames: { names: string[]; value: number }[][] = []
    let settled = false
    const unsubscribe = subscribeCrossfilter({
      onLive: (query) => frames.push(dataset.countsSync(['type'], query)),
      onSettle: () => (settled = true)
    })

    publishLive('value:>15')
    flushFrame()
    expect(frames).toEqual([
      [
        { names: ['B'], value: 1 },
        { names: ['A'], value: 1 }
      ]
    ])

    publishSettle()
    expect(settled).toBe(true)
    unsubscribe()
  })
})
