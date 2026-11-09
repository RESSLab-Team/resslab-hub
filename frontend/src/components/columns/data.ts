/**
 * Columns dataset source for the in-browser query layer (`useDataset`):
 * the full table, fetched once through the existing paginated list endpoint.
 */
import { ColumnField, type ColumnModel, ColumnNumberField } from '@/backend'
import type { DatasetSource, ParallelField } from '@/composables/chart'
import { columnsApi } from '@/plugins/axios'
import { fetchAllPages } from '@/utils/backend'

export const COLUMN_KEY = 'column'

export const fetchColumns = (): Promise<ColumnModel[]> =>
  fetchAllPages((page, size) => columnsApi.getColumns(undefined, undefined, undefined, page, size))

/** What the dashboard charts (`commons/charts/Dataset*Chart.vue`) read this dataset with. */
export const COLUMN_SOURCE: DatasetSource<ColumnField> = {
  key: COLUMN_KEY,
  fetchAll: fetchColumns,
  labelPrefix: 'column.',
  idField: ColumnField.Id,
  numberFields: ColumnNumberField
}

/** Parallel-coordinates axes, shared by the dashboard and the curation ghost view. */
export const PARALLEL_FIELDS: ParallelField<ColumnField>[] = [
  { id: ColumnField.Th80 },
  { id: ColumnField.HOverTCw },
  { id: ColumnField.BFOverTCf },
  { id: ColumnField.LBOverRYc },
  { id: ColumnField.PGOverPYm }
]
