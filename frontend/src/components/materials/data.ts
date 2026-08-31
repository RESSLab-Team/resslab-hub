/**
 * Materials dataset source for the in-browser query layer (`useDataset`):
 * the full table, fetched once through the existing paginated list endpoint.
 */
import { MaterialField, type MaterialModel } from '@/backend'
import type { ParallelField } from '@/composables/chart'
import { materialsApi } from '@/plugins/axios'
import { fetchAllPages } from '@/utils/backend'

export const MATERIAL_KEY = 'material'

export const fetchMaterials = (): Promise<MaterialModel[]> =>
  fetchAllPages((page, size) =>
    materialsApi.getMaterials(undefined, undefined, undefined, page, size)
  )

/** Parallel-coordinates axes, shared by the dashboard and the curation ghost view. */
export const PARALLEL_FIELDS: ParallelField<MaterialField>[] = [
  { id: MaterialField.Type },
  { id: MaterialField.YieldStressMpa },
  {
    id: {
      dividend: MaterialField.YieldStressMpa,
      divisor: MaterialField.FyNMpa
    }
  },
  { id: MaterialField.FractureStrain },
  { id: MaterialField.Thickness }
]
