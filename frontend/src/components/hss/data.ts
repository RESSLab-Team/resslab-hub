/**
 * Hss dataset source for the in-browser query layer (`useDataset`):
 * the full table, fetched once through the existing paginated list endpoint.
 */
import { HSSColumnField, type HSSColumnModel, HSSColumnNumberField } from '@/backend'
import type { DatasetSource, ParallelField } from '@/composables/chart'
import { hssApi } from '@/plugins/axios'
import { fetchAllPages } from '@/utils/backend'
import { testConfigurationNameMapping } from '@/utils/hss'

export const HSS_KEY = 'hss'

export const fetchHsss = (): Promise<HSSColumnModel[]> =>
  fetchAllPages((page, size) => hssApi.getHssColumns(undefined, undefined, undefined, page, size))

/** What the dashboard charts (`commons/charts/Dataset*Chart.vue`) read this dataset with. */
export const HSS_SOURCE: DatasetSource<HSSColumnField> = {
  key: HSS_KEY,
  fetchAll: fetchHsss,
  labelPrefix: 'hss.',
  idField: HSSColumnField.Id,
  numberFields: HSSColumnNumberField
}

/**
 * Parallel-coordinates axes, shared by the dashboard and the curation ghost
 * view. A function, unlike the other databases' PARALLEL_FIELDS, because the
 * configuration axis carries translated labels.
 */
export function parallelFields(): ParallelField<HSSColumnField>[] {
  return [
    { id: HSSColumnField.ThetaPPos100fitRad, name: 'θp [rad]' },
    { id: HSSColumnField.DepthOverT, name: 'D/t' },
    { id: HSSColumnField.AxialLoadRatio, name: 'Pg/Py' },
    { id: HSSColumnField.LoadingAngle, name: 'Load Angle [degrees]' },
    {
      id: HSSColumnField.TestConfiguration,
      name: 'Configuration',
      mapping: testConfigurationNameMapping()
    }
  ]
}
