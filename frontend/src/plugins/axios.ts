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
import { Configuration } from '@/backend/configuration'
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

// `/validate` sits behind HTTP Basic auth. The contribution pipeline has no real
// identity yet, so the dev credentials are carried here; a deployment that
// exposes contribution beyond localhost needs the real user's token instead.
export const defaultApi = new DefaultApi(
  new Configuration({
    username: import.meta.env.VITE_APP_API_USERNAME,
    password: import.meta.env.VITE_APP_API_PASSWORD
  }),
  baseUrl,
  axiosInstance
)
