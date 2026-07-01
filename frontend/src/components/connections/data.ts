/**
 * Connections dataset source for the in-browser query layer (`useDataset`):
 * the full table, fetched once through the existing paginated list endpoint.
 */
import type { ConnectionModel } from '@/backend'
import { connectionsApi } from '@/plugins/axios'
import { fetchAllPages } from '@/utils/backend'

export const CONNECTION_KEY = 'connection'

export const fetchConnections = (): Promise<ConnectionModel[]> =>
  fetchAllPages((page, size) =>
    connectionsApi.getConnections(undefined, undefined, undefined, page, size)
  )
