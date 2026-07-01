/**
 * Eccentric braced frames dataset source for the in-browser query layer
 * (`useDataset`).
 *
 * Fetches the full EBF table once via the existing paginated list endpoint,
 * then all filtering/aggregation happens client-side.
 */
import type { EccentricBracedFrameModel } from '@/backend'
import { ebfApi } from '@/plugins/axios'

export const EBF_KEY = 'ebf'

const PAGE_SIZE = 1000

export async function fetchEbfs(): Promise<EccentricBracedFrameModel[]> {
  const all: EccentricBracedFrameModel[] = []
  let page = 1
  for (;;) {
    const { data } = await ebfApi.getEccentricBracedFrames(
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
