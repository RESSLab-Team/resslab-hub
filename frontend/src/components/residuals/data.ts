/**
 * Residuals dataset source for the in-browser query layer (`useDataset`).
 *
 * Fetches the full residual-stresses table once via the existing paginated list
 * endpoint, then all filtering/aggregation happens client-side.
 */
import type { ResidualStressModel } from '@/backend'
import { residualsApi } from '@/plugins/axios'

export const RESIDUAL_KEY = 'residual'

const PAGE_SIZE = 1000

export async function fetchResiduals(): Promise<ResidualStressModel[]> {
  const all: ResidualStressModel[] = []
  let page = 1
  for (;;) {
    const { data } = await residualsApi.getResidualStresses(
      undefined,
      undefined,
      undefined,
      page,
      PAGE_SIZE
    )
    all.push(...data.items)
    const total = data.total ?? all.length
    if (data.items.length === 0 || all.length >= total) break
    page += 1
  }
  return all
}
