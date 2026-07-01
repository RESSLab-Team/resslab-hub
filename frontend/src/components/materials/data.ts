/**
 * Materials dataset source for the in-browser query layer (`useDataset`).
 *
 * Fetches the full materials table once via the existing paginated list
 * endpoint, then all filtering/aggregation happens client-side.
 */
import type { MaterialModel } from '@/backend'
import { materialsApi } from '@/plugins/axios'

export const MATERIAL_KEY = 'material'

const PAGE_SIZE = 1000

export async function fetchMaterials(): Promise<MaterialModel[]> {
  const all: MaterialModel[] = []
  let page = 1
  for (;;) {
    const { data } = await materialsApi.getMaterials(
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
