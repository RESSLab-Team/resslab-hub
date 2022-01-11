import { ColumnsApi, ConnectionsApi } from "@/backend";

declare module "vue/types/vue" {
  interface Vue {
    $columnsApi: ColumnsApi;
    $connectionsApi: ConnectionsApi;
  }
}
