export interface Page<T> {
  items: T[]
  total: number
  page?: number
  size?: number
}

/**
 * Drain a paginated list endpoint into one array — the fetcher shape
 * `useDataset` expects. Structural response type so any generated API client
 * page model fits.
 *
 * The first page tells us `total`, so every other page is requested at once
 * rather than one after the other: at 10 000 rows that is nine round-trips
 * overlapping instead of queueing (#354). The pages come back in order
 * whatever order they finish in. Only when the endpoint gives no `total` do we
 * fall back to walking page by page until one comes back empty.
 */
export async function fetchAllPages<T>(
  getPage: (page: number, size: number) => Promise<{ data: { items: T[]; total?: number | null } }>,
  pageSize = 1000
): Promise<T[]> {
  const first = (await getPage(1, pageSize)).data
  const all: T[] = [...first.items]
  if (first.items.length === 0) return all

  if (first.total != null) {
    const pages = Math.ceil(first.total / pageSize)
    if (pages <= 1) return all
    const rest = await Promise.all(
      Array.from({ length: pages - 1 }, (_, i) => getPage(i + 2, pageSize))
    )
    for (const { data } of rest) all.push(...data.items)
    return all
  }

  for (let page = 2; ; page += 1) {
    const { data } = await getPage(page, pageSize)
    if (data.items.length === 0) break
    all.push(...data.items)
  }
  return all
}

export type Type =
  | 'Braces'
  | 'Columns'
  | 'Connections'
  | 'Cyclic Coupons'
  | 'Tensile Coupons'
  | 'Ductile Fracture'
  | 'Residual Stresses'
  | 'HSS Columns'
  | 'EBF Links'
export const typesNames: Type[] = [
  'Braces',
  'Columns',
  'Connections',
  'Cyclic Coupons',
  'Tensile Coupons',
  'Ductile Fracture',
  'Residual Stresses',
  'HSS Columns',
  'EBF Links'
]
