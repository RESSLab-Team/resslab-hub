import { BracesApi, ColumnsApi, ConnectionsApi, MaterialsApi } from "@/backend";
import axios from "axios";
import Vue from "vue";

const axiosInstance = axios.create();
const baseUrl = process.env.VUE_APP_BACKEND_URL;

export const bracesApi = new BracesApi(undefined, baseUrl, axiosInstance);
export const columnsApi = new ColumnsApi(undefined, baseUrl, axiosInstance);
export const connectionsApi = new ConnectionsApi(
  undefined,
  baseUrl,
  axiosInstance
);
export const materialsApi = new MaterialsApi(undefined, baseUrl, axiosInstance);

Vue.prototype.$bracesApi = bracesApi;
Vue.prototype.$columnsApi = columnsApi;
Vue.prototype.$connectionsApi = connectionsApi;
Vue.prototype.$materialsApi = materialsApi;
