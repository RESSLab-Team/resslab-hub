/**
 * Residuals dataset source for the in-browser query layer (`useDataset`):
 * the full table, fetched once through the existing paginated list endpoint.
 */
import { ResidualStressField, type ResidualStressModel } from '@/backend'
import type { ParallelField } from '@/composables/chart'
import { residualsApi } from '@/plugins/axios'
import { fetchAllPages } from '@/utils/backend'

export const RESIDUAL_KEY = 'residual'

export const fetchResiduals = (): Promise<ResidualStressModel[]> =>
  fetchAllPages((page, size) =>
    residualsApi.getResidualStresses(undefined, undefined, undefined, page, size)
  )

/** Parallel-coordinates axes, shared by the dashboard and the curation ghost view. */
export const PARALLEL_FIELDS: ParallelField<ResidualStressField>[] = [
  { id: ResidualStressField.Steel, name: 'Steel Grade' },
  { id: ResidualStressField.HOverB, name: 'h/bf' },
  { id: ResidualStressField.Tf, name: 'tf [mm]' },
  { id: ResidualStressField.A, name: 'A [mm²]' },
  { id: ResidualStressField.Sigma0F, name: 'σ0,f [MPa]' },
  { id: ResidualStressField.Sigma0W, name: 'σ0,w [MPa] ' }
]
