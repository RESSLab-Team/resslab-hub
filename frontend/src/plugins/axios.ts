import { ConnectionsApi } from "@/backend";
import axios from "axios";
import Vue from "vue";

const axiosInstance = axios.create();
const baseUrl = process.env.VUE_APP_BACKEND_URL;
Vue.prototype.$connectionsApi = new ConnectionsApi(
  undefined,
  baseUrl,
  axiosInstance
);
