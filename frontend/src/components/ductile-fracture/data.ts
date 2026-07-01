/**
 * Ductile-fracture dataset source for the in-browser query layer (`useDataset`).
 *
 * Fetches the full ductile-fracture table once via the existing paginated list
 * endpoint, then all filtering/aggregation happens client-side.
 */
import type { DuctileFractureModel } from '@/backend'
import { ductileFractureApi } from '@/plugins/axios'

export const DUCTILE_FRACTURE_KEY = 'ductile-fracture'

const PAGE_SIZE = 1000

export async function fetchDuctileFractures(): Promise<DuctileFractureModel[]> {
  const all: DuctileFractureModel[] = []
  let page = 1
  for (;;) {
    const { data } = await ductileFractureApi.getDuctileFractures(
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
