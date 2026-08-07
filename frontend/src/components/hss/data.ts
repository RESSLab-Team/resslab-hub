/**
 * Hss dataset source for the in-browser query layer (`useDataset`):
 * the full table, fetched once through the existing paginated list endpoint.
 */
import { HSSColumnField, type HSSColumnModel } from '@/backend'
import type { ParallelField } from '@/composables/chart'
import { hssApi } from '@/plugins/axios'
import { fetchAllPages } from '@/utils/backend'
import { testConfigurationNameMapping } from '@/utils/hss'

export const HSS_KEY = 'hss'

export const fetchHsss = (): Promise<HSSColumnModel[]> =>
  fetchAllPages((page, size) => hssApi.getHssColumns(undefined, undefined, undefined, page, size))

/** Parallel-coordinates axes, shared by the dashboard and the curation ghost view. */
export const PARALLEL_FIELDS: ParallelField<HSSColumnField>[] = [
  { id: HSSColumnField.ThetaPPos100fitRad, name: 'θp [rad]' },
  { id: HSSColumnField.DepthOverT, name: 'D/t' },
  { id: HSSColumnField.AxialLoadRatio, name: 'Pg/Py' },
  { id: HSSColumnField.LoadingAngle, name: 'Load Angle [degrees]' },
  {
    id: HSSColumnField.TestConfiguration,
    name: 'Configuration',
    mapping: testConfigurationNameMapping
  }
]
