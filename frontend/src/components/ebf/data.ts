/**
 * Eccentric braced frames dataset source for the in-browser query layer (`useDataset`):
 * the full table, fetched once through the existing paginated list endpoint.
 */
import {
  EccentricBracedFrameField,
  type EccentricBracedFrameModel,
  EccentricBracedFrameNumberField
} from '@/backend'
import type { DatasetSource } from '@/composables/chart'
import { ebfApi } from '@/plugins/axios'
import { fetchAllPages } from '@/utils/backend'

export const EBF_KEY = 'ebf'

export const fetchEbfs = (): Promise<EccentricBracedFrameModel[]> =>
  fetchAllPages((page, size) =>
    ebfApi.getEccentricBracedFrames(undefined, undefined, undefined, page, size)
  )

/** What the dashboard charts (`commons/charts/Dataset*Chart.vue`) read this dataset with. */
export const EBF_SOURCE: DatasetSource<EccentricBracedFrameField> = {
  key: EBF_KEY,
  fetchAll: fetchEbfs,
  labelPrefix: 'ebf.',
  idField: EccentricBracedFrameField.Id,
  numberFields: EccentricBracedFrameNumberField
}
