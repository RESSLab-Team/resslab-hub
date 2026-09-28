/**
 * Connections dataset source for the in-browser query layer (`useDataset`):
 * the full table, fetched once through the existing paginated list endpoint.
 */
import { ConnectionField, type ConnectionModel } from '@/backend'
import type { ParallelField } from '@/composables/chart'
import { connectionsApi } from '@/plugins/axios'
import { fetchAllPages } from '@/utils/backend'

export const CONNECTION_KEY = 'connection'

export const fetchConnections = (): Promise<ConnectionModel[]> =>
  fetchAllPages((page, size) =>
    connectionsApi.getConnections(undefined, undefined, undefined, page, size)
  )

/** Parallel-coordinates axes, shared by the dashboard and the curation ghost view. */
export const PARALLEL_FIELDS: ParallelField<ConnectionField>[] = [
  {
    id: ConnectionField.DB,
    name: 'Beam Depth\ndb [mm]'
  },
  {
    id: ConnectionField.DC,
    name: 'Column Depth\ndc [mm]'
  },
  {
    id: ConnectionField.TCf,
    name: 'Column flange\nThickness [mm]'
  },
  {
    id: {
      dividend: ConnectionField.DB,
      divisor: ConnectionField.DC
    },
    name: 'db / dc'
  },
  {
    id: ConnectionField.GMaxGY
  },
  {
    id: ConnectionField.RuRnPlN
  },
  {
    id: ConnectionField.ConnectionType,
    name: 'Connection\nType'
  }
]
