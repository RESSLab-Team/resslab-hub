import { BracesApi, ColumnsApi, ConnectionsApi, MaterialsApi } from "@/backend";
import axios from "axios";
import Vue from "vue";

const axiosInstance = axios.create();
const baseUrl = process.env.VUE_APP_BACKEND_URL;

Vue.prototype.$bracesApi = new BracesApi(undefined, baseUrl, axiosInstance);
Vue.prototype.$columnsApi = new ColumnsApi(undefined, baseUrl, axiosInstance);
Vue.prototype.$connectionsApi = new ConnectionsApi(
  undefined,
  baseUrl,
  axiosInstance
);
Vue.prototype.$materialsApi = new MaterialsApi(
  undefined,
  baseUrl,
  axiosInstance
);
