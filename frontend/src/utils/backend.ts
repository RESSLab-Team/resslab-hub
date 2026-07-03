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
 */
export async function fetchAllPages<T>(
  getPage: (page: number, size: number) => Promise<{ data: { items: T[]; total?: number | null } }>,
  pageSize = 1000
): Promise<T[]> {
  const all: T[] = []
  let page = 1
  for (;;) {
    const { data } = await getPage(page, pageSize)
    all.push(...data.items)
    const total = data.total ?? all.length
    if (data.items.length === 0 || all.length >= total) break
    page += 1
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
