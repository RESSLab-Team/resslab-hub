/**
 * Tensile coupons dataset source for the in-browser query layer (`useDataset`):
 * the full table, fetched once through the existing paginated list endpoint.
 */
import type { TensileCouponModel } from '@/backend'
import { tensileCouponApi } from '@/plugins/axios'
import { fetchAllPages } from '@/utils/backend'

export const TENSILE_COUPON_KEY = 'tensile-coupon'

export const fetchTensileCoupons = (): Promise<TensileCouponModel[]> =>
  fetchAllPages((page, size) =>
    tensileCouponApi.getTensileCoupons(undefined, undefined, undefined, page, size)
  )
