/**
 * Columns dataset source for the in-browser query layer (`useDataset`).
 *
 * Fetches the full columns table once via the existing paginated list
 * endpoint, then all filtering/aggregation happens client-side.
 */
import type { ColumnModel } from '@/backend'
import { columnsApi } from '@/plugins/axios'

export const COLUMN_KEY = 'column'

const PAGE_SIZE = 1000

export async function fetchColumns(): Promise<ColumnModel[]> {
  const all: ColumnModel[] = []
  let page = 1
  for (;;) {
    const { data } = await columnsApi.getColumns(
      undefined,
      undefined,
      undefined,
      page,
      PAGE_SIZE
    )
    all.push(...data.items)
    const total = data.total ?? all.length
    if (data.items.length === 0 || all.length >= total) break
    page += 1
  }
  return all
}
