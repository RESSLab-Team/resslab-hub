/**
 * Braces dataset source for the in-browser query layer (`useDataset`):
 * the full table, fetched once through the existing paginated list endpoint.
 */
import type { BraceModel } from '@/backend'
import { bracesApi } from '@/plugins/axios'
import { fetchAllPages } from '@/utils/backend'

export const BRACE_KEY = 'brace'

export const fetchBraces = (): Promise<BraceModel[]> =>
  fetchAllPages((page, size) => bracesApi.getBraces(undefined, undefined, undefined, page, size))
