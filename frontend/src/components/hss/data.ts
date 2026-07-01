/**
 * Hss dataset source for the in-browser query layer (`useDataset`).
 *
 * Fetches the full hss table once via the existing paginated list
 * endpoint, then all filtering/aggregation happens client-side.
 */
import type { HSSColumnModel } from '@/backend'
import { hssApi } from '@/plugins/axios'

export const HSS_KEY = 'hss'

const PAGE_SIZE = 1000

export async function fetchHsss(): Promise<HSSColumnModel[]> {
  const all: HSSColumnModel[] = []
  let page = 1
  for (;;) {
    const { data } = await hssApi.getHssColumns(undefined, undefined, undefined, page, PAGE_SIZE)
    all.push(...data.items)
    const total = data.total ?? all.length
    if (data.items.length === 0 || all.length >= total) break
    page += 1
  }
  return all
}
