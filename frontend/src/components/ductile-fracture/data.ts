/**
 * Ductile-fracture dataset source for the in-browser query layer (`useDataset`):
 * the full table, fetched once through the existing paginated list endpoint.
 */
import {
  DuctileFractureField,
  type DuctileFractureModel,
  DuctileFractureNumberField
} from '@/backend'
import type { DatasetSource } from '@/composables/chart'
import { ductileFractureApi } from '@/plugins/axios'
import { fetchAllPages } from '@/utils/backend'

export const DUCTILE_FRACTURE_KEY = 'ductile-fracture'

export const fetchDuctileFractures = (): Promise<DuctileFractureModel[]> =>
  fetchAllPages((page, size) =>
    ductileFractureApi.getDuctileFractures(undefined, undefined, undefined, page, size)
  )

/** What the dashboard charts (`commons/charts/Dataset*Chart.vue`) read this dataset with. */
export const DUCTILE_FRACTURE_SOURCE: DatasetSource<DuctileFractureField> = {
  key: DUCTILE_FRACTURE_KEY,
  fetchAll: fetchDuctileFractures,
  labelPrefix: 'ductile_fracture.',
  idField: DuctileFractureField.Id,
  numberFields: DuctileFractureNumberField
}
