/**
 * Braces dataset source for the in-browser query layer (`useDataset`):
 * the full table, fetched once through the existing paginated list endpoint.
 */
import { BraceField, type BraceModel } from '@/backend'
import type { ParallelField } from '@/composables/chart'
import { bracesApi } from '@/plugins/axios'
import { fetchAllPages } from '@/utils/backend'

export const BRACE_KEY = 'brace'

export const fetchBraces = (): Promise<BraceModel[]> =>
  fetchAllPages((page, size) => bracesApi.getBraces(undefined, undefined, undefined, page, size))

/** Parallel-coordinates axes, shared by the dashboard and the curation ghost view. */
export const PARALLEL_FIELDS: ParallelField<BraceField>[] = [
  { id: BraceField.KlR },
  {
    id: {
      dividend: BraceField.DBr,
      divisor: BraceField.TBr
    }
  },
  { id: BraceField.CrossSectionShape },
  { id: BraceField.BoundaryCondition }
]
