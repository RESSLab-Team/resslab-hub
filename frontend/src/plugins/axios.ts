import {
  AnalyticsApi,
  BracesApi,
  ColumnsApi,
  ConnectionsApi,
  MaterialsApi,
} from "@/backend";
import axios from "axios";

const axiosInstance = axios.create();
const baseUrl = process.env.VUE_APP_BACKEND_URL;

export const analyticsApi = new AnalyticsApi(undefined, baseUrl, axiosInstance);
export const bracesApi = new BracesApi(undefined, baseUrl, axiosInstance);
export const columnsApi = new ColumnsApi(undefined, baseUrl, axiosInstance);
export const connectionsApi = new ConnectionsApi(
  undefined,
  baseUrl,
  axiosInstance
);
export const materialsApi = new MaterialsApi(undefined, baseUrl, axiosInstance);
