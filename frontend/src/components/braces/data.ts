/**
 * Braces dataset source for the in-browser query layer (`useDataset`).
 *
 * Fetches the full braces table once via the existing paginated list
 * endpoint, then all filtering/aggregation happens client-side.
 */
import type { BraceModel } from '@/backend'
import { bracesApi } from '@/plugins/axios'

export const BRACE_KEY = 'brace'

const PAGE_SIZE = 1000

export async function fetchBraces(): Promise<BraceModel[]> {
  const all: BraceModel[] = []
  let page = 1
  for (;;) {
    const { data } = await bracesApi.getBraces(undefined, undefined, undefined, page, PAGE_SIZE)
    all.push(...data.items)
    const total = data.total ?? all.length
    if (data.items.length === 0 || all.length >= total) break
    page += 1
  }
  return all
}
