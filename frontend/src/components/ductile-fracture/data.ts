/**
 * Ductile-fracture dataset source for the in-browser query layer (`useDataset`):
 * the full table, fetched once through the existing paginated list endpoint.
 */
import type { DuctileFractureModel } from '@/backend'
import { ductileFractureApi } from '@/plugins/axios'
import { fetchAllPages } from '@/utils/backend'

export const DUCTILE_FRACTURE_KEY = 'ductile-fracture'

export const fetchDuctileFractures = (): Promise<DuctileFractureModel[]> =>
  fetchAllPages((page, size) =>
    ductileFractureApi.getDuctileFractures(undefined, undefined, undefined, page, size)
  )
