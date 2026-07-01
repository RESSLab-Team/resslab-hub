/**
 * Residuals dataset source for the in-browser query layer (`useDataset`):
 * the full table, fetched once through the existing paginated list endpoint.
 */
import type { ResidualStressModel } from '@/backend'
import { residualsApi } from '@/plugins/axios'
import { fetchAllPages } from '@/utils/backend'

export const RESIDUAL_KEY = 'residual'

export const fetchResiduals = (): Promise<ResidualStressModel[]> =>
  fetchAllPages((page, size) =>
    residualsApi.getResidualStresses(undefined, undefined, undefined, page, size)
  )
