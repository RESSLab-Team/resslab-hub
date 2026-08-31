/**
 * Eccentric braced frames dataset source for the in-browser query layer (`useDataset`):
 * the full table, fetched once through the existing paginated list endpoint.
 */
import type { EccentricBracedFrameModel } from '@/backend'
import { ebfApi } from '@/plugins/axios'
import { fetchAllPages } from '@/utils/backend'

export const EBF_KEY = 'ebf'

export const fetchEbfs = (): Promise<EccentricBracedFrameModel[]> =>
  fetchAllPages((page, size) =>
    ebfApi.getEccentricBracedFrames(undefined, undefined, undefined, page, size)
  )
