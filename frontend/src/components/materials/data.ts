/**
 * Materials dataset source for the in-browser query layer (`useDataset`):
 * the full table, fetched once through the existing paginated list endpoint.
 */
import {
  MaterialDateField,
  MaterialField,
  type MaterialModel,
  MaterialNumberField
} from '@/backend'
import type { DatasetSource, ParallelField } from '@/composables/chart'
import { materialsApi } from '@/plugins/axios'
import { fetchAllPages } from '@/utils/backend'

export const MATERIAL_KEY = 'material'

export const fetchMaterials = (): Promise<MaterialModel[]> =>
  fetchAllPages((page, size) =>
    materialsApi.getMaterials(undefined, undefined, undefined, page, size)
  )

/** What the dashboard charts (`commons/charts/Dataset*Chart.vue`) read this dataset with. */
export const MATERIAL_SOURCE: DatasetSource<MaterialField> = {
  key: MATERIAL_KEY,
  fetchAll: fetchMaterials,
  labelPrefix: 'material.',
  idField: MaterialField.Id,
  numberFields: MaterialNumberField,
  dateFields: MaterialDateField
}

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
