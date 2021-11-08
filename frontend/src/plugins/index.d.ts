import Vue, { VueConstructor } from "vue";

import { AxiosInstance } from "axios";
import { ConnectionsApi } from "@/backend";

declare module "vue/types/vue" {
  interface Vue {
    $connectionsApi: ConnectionsApi;
  }
}
