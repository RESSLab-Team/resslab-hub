/**
 * Connections dataset source for the in-browser query layer (`useDataset`).
 *
 * Fetches the full connections table once via the existing paginated list
 * endpoint, then all filtering/aggregation happens client-side.
 */
import type { ConnectionModel } from '@/backend'
import { connectionsApi } from '@/plugins/axios'

export const CONNECTION_KEY = 'connection'

const PAGE_SIZE = 1000

export async function fetchConnections(): Promise<ConnectionModel[]> {
  const all: ConnectionModel[] = []
  let page = 1
  for (;;) {
    const { data } = await connectionsApi.getConnections(
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
