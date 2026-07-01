/**
 * Columns dataset source for the in-browser query layer (`useDataset`):
 * the full table, fetched once through the existing paginated list endpoint.
 */
import type { ColumnModel } from '@/backend'
import { columnsApi } from '@/plugins/axios'
import { fetchAllPages } from '@/utils/backend'

export const COLUMN_KEY = 'column'

export const fetchColumns = (): Promise<ColumnModel[]> =>
  fetchAllPages((page, size) => columnsApi.getColumns(undefined, undefined, undefined, page, size))
