/**
 * Columns dataset source for the in-browser query layer (`useDataset`):
 * the full table, fetched once through the existing paginated list endpoint.
 */
import { ColumnField, type ColumnModel } from '@/backend'
import type { ParallelField } from '@/composables/chart'
import { columnsApi } from '@/plugins/axios'
import { fetchAllPages } from '@/utils/backend'

export const COLUMN_KEY = 'column'

export const fetchColumns = (): Promise<ColumnModel[]> =>
  fetchAllPages((page, size) => columnsApi.getColumns(undefined, undefined, undefined, page, size))

/** Parallel-coordinates axes, shared by the dashboard and the curation ghost view. */
export const PARALLEL_FIELDS: ParallelField<ColumnField>[] = [
  { id: ColumnField.Th80 },
  { id: ColumnField.HOverTCw },
  { id: ColumnField.BFOverTCf },
  { id: ColumnField.LBOverRYc },
  { id: ColumnField.PGOverPYm }
]
