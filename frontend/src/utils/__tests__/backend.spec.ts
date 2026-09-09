import { fetchAllPages } from '@/utils/backend'
import { describe, expect, it, vi } from 'vitest'

/**
 * `fetchAllPages` feeds every dashboard, so the contract is spelled out here:
 * every row, once, in page order, and the pages after the first requested
 * together rather than one after the other (#354).
 */
function server(total: number, delays: number[] = []) {
  const calls: number[] = []
  const inFlight = { now: 0, peak: 0 }
  const getPage = vi.fn(async (page: number, size: number) => {
    calls.push(page)
    inFlight.now += 1
    inFlight.peak = Math.max(inFlight.peak, inFlight.now)
    await new Promise((resolve) => setTimeout(resolve, delays[page - 1] ?? 0))
    inFlight.now -= 1
    const start = (page - 1) * size
    const items = Array.from({ length: Math.max(0, Math.min(size, total - start)) }, (_, i) => ({
      id: start + i
    }))
    return { data: { items, total } }
  })
  return { getPage, calls, inFlight }
}

describe('fetchAllPages', () => {
  it('returns every row in page order', async () => {
    const { getPage } = server(25)
    const rows = await fetchAllPages(getPage, 10)
    expect(rows.map((row) => row.id)).toEqual(Array.from({ length: 25 }, (_, i) => i))
  })

  it('asks for the pages after the first all at once', async () => {
    const { getPage, calls, inFlight } = server(45, [5, 5, 5, 5, 5])
    await fetchAllPages(getPage, 10)
    expect(calls).toEqual([1, 2, 3, 4, 5])
    expect(inFlight.peak).toBe(4)
  })

  it('keeps page order even when later pages answer first', async () => {
    const { getPage } = server(30, [0, 30, 1])
    const rows = await fetchAllPages(getPage, 10)
    expect(rows.map((row) => row.id)).toEqual(Array.from({ length: 30 }, (_, i) => i))
  })

  it('stops after one request when everything fits in the first page', async () => {
    const { getPage, calls } = server(7)
    const rows = await fetchAllPages(getPage, 10)
    expect(rows).toHaveLength(7)
    expect(calls).toEqual([1])
  })

  it('handles an empty table', async () => {
    const { getPage, calls } = server(0)
    expect(await fetchAllPages(getPage, 10)).toEqual([])
    expect(calls).toEqual([1])
  })

  it('walks page by page when the endpoint gives no total', async () => {
    const pages = [[{ id: 0 }, { id: 1 }], [{ id: 2 }], []]
    const getPage = vi.fn(async (page: number) => ({
      data: { items: pages[page - 1] ?? [], total: null }
    }))
    const rows = await fetchAllPages(getPage, 2)
    expect(rows.map((row) => row.id)).toEqual([0, 1, 2])
    expect(getPage).toHaveBeenCalledTimes(3)
  })
})
