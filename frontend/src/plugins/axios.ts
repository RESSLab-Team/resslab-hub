import {
  AnalyticsApi,
  BracesApi,
  ColumnsApi,
  ConnectionsApi,
  HssColumnApi,
  MaterialsApi,
  ResidualStressApi
} from '@/backend/api'
import axios from 'axios'

const axiosInstance = axios.create()
const baseUrl = import.meta.env.VITE_APP_BACKEND_URL

export const analyticsApi = new AnalyticsApi(undefined, baseUrl, axiosInstance)
export const bracesApi = new BracesApi(undefined, baseUrl, axiosInstance)
export const columnsApi = new ColumnsApi(undefined, baseUrl, axiosInstance)
export const connectionsApi = new ConnectionsApi(undefined, baseUrl, axiosInstance)
export const materialsApi = new MaterialsApi(undefined, baseUrl, axiosInstance)
export const residualsApi = new ResidualStressApi(undefined, baseUrl, axiosInstance)
export const hssApi = new HssColumnApi(undefined, baseUrl, axiosInstance)
