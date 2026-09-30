import {
  AnalyticsApi,
  AuthApi,
  BracesApi,
  ColumnsApi,
  ConnectionsApi,
  DefaultApi,
  DuctileFractureApi,
  EccentricBracedFrameApi,
  HssColumnApi,
  MapApi,
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
export const mapApi = new MapApi(undefined, baseUrl, axiosInstance)

export const defaultApi = new DefaultApi(undefined, baseUrl, axiosInstance)
export const authApi = new AuthApi(undefined, baseUrl, axiosInstance)

// Sign-in rides on an httpOnly session cookie (#247), so nothing is carried in
// the bundle and nothing is read by JavaScript. The app is same-origin in every
// environment (Traefik in the deployments, the Vite proxy in development), so
// the browser attaches the cookie on its own and `withCredentials` is not
// needed.
//
// A 401 means the session went away: the cookie expired, or someone signed out
// in another tab. Drop the cached user so the interface stops showing them as
// signed in; the router guard sends them to the sign-in page on the next
// navigation to a page that needs one.
axiosInstance.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error?.response?.status === 401) {
      const { useAuthStore } = await import('@/stores/auth')
      useAuthStore().clear()
    }
    return Promise.reject(error)
  }
)
