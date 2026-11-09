/**
 * Tensile coupons dataset source for the in-browser query layer (`useDataset`):
 * the full table, fetched once through the existing paginated list endpoint.
 */
import { TensileCouponField, type TensileCouponModel, TensileCouponNumberField } from '@/backend'
import type { DatasetSource } from '@/composables/chart'
import { tensileCouponApi } from '@/plugins/axios'
import { fetchAllPages } from '@/utils/backend'

export const TENSILE_COUPON_KEY = 'tensile-coupon'

export const fetchTensileCoupons = (): Promise<TensileCouponModel[]> =>
  fetchAllPages((page, size) =>
    tensileCouponApi.getTensileCoupons(undefined, undefined, undefined, page, size)
  )

/** What the dashboard charts (`commons/charts/Dataset*Chart.vue`) read this dataset with. */
export const TENSILE_COUPON_SOURCE: DatasetSource<TensileCouponField> = {
  key: TENSILE_COUPON_KEY,
  fetchAll: fetchTensileCoupons,
  labelPrefix: 'tensile_coupon.',
  idField: TensileCouponField.Id,
  numberFields: TensileCouponNumberField
}
