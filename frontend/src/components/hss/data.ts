/**
 * Hss dataset source for the in-browser query layer (`useDataset`):
 * the full table, fetched once through the existing paginated list endpoint.
 */
import type { HSSColumnModel } from '@/backend'
import { hssApi } from '@/plugins/axios'
import { fetchAllPages } from '@/utils/backend'

export const HSS_KEY = 'hss'

export const fetchHsss = (): Promise<HSSColumnModel[]> =>
  fetchAllPages((page, size) => hssApi.getHssColumns(undefined, undefined, undefined, page, size))
