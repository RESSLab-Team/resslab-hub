/**
 * Materials dataset source for the in-browser query layer (`useDataset`):
 * the full table, fetched once through the existing paginated list endpoint.
 */
import type { MaterialModel } from '@/backend'
import { materialsApi } from '@/plugins/axios'
import { fetchAllPages } from '@/utils/backend'

export const MATERIAL_KEY = 'material'

export const fetchMaterials = (): Promise<MaterialModel[]> =>
  fetchAllPages((page, size) =>
    materialsApi.getMaterials(undefined, undefined, undefined, page, size)
  )
