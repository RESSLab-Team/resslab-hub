import {
  AnalyticsApi,
  BracesApi,
  ColumnsApi,
  ConnectionsApi,
  DefaultApi,
  DuctileFractureApi,
  EccentricBracedFrameApi,
  HssColumnApi,
  MaterialsApi,
  ResidualStressApi,
  TensileCouponApi
} from '@/backend/api'
import axios from 'axios'

// Exported for hand-written calls to endpoints the generated client does not
// cover.
export const axiosInstance = axios.create()
export const baseUrl = import.meta.env.VITE_APP_BACKEND_URL

export const analyticsApi = new AnalyticsApi(undefined, baseUrl, axiosInstance)
export const bracesApi = new BracesApi(undefined, baseUrl, axiosInstance)
export const columnsApi = new ColumnsApi(undefined, baseUrl, axiosInstance)
export const connectionsApi = new ConnectionsApi(undefined, baseUrl, axiosInstance)
export const materialsApi = new MaterialsApi(undefined, baseUrl, axiosInstance)
export const residualsApi = new ResidualStressApi(undefined, baseUrl, axiosInstance)
export const hssApi = new HssColumnApi(undefined, baseUrl, axiosInstance)
export const ebfApi = new EccentricBracedFrameApi(undefined, baseUrl, axiosInstance)
export const tensileCouponApi = new TensileCouponApi(undefined, baseUrl, axiosInstance)
export const ductileFractureApi = new DuctileFractureApi(undefined, baseUrl, axiosInstance)

// The contribution pipeline's two endpoints — `/validate` and `/contributions`
// — are both open, so no credentials are carried here. They must stay that way
// until #247 gives contributors a real identity: the shared HTTP Basic password
// also guards `/upload`, and anything the browser sends ships in the bundle.
export const defaultApi = new DefaultApi(undefined, baseUrl, axiosInstance)
