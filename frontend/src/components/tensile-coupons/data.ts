/**
 * Tensile coupons dataset source for the in-browser query layer (`useDataset`).
 *
 * Fetches the full tensile coupons table once via the existing paginated list
 * endpoint, then all filtering/aggregation happens client-side.
 */
import type { TensileCouponModel } from '@/backend'
import { tensileCouponApi } from '@/plugins/axios'

export const TENSILE_COUPON_KEY = 'tensile-coupon'

const PAGE_SIZE = 1000

export async function fetchTensileCoupons(): Promise<TensileCouponModel[]> {
  const all: TensileCouponModel[] = []
  let page = 1
  for (;;) {
    const { data } = await tensileCouponApi.getTensileCoupons(
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
