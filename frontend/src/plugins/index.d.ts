import { BracesApi, ColumnsApi, ConnectionsApi } from "@/backend";

declare module "vue/types/vue" {
  interface Vue {
    $bracesApi: BracesApi;
    $columnsApi: ColumnsApi;
    $connectionsApi: ConnectionsApi;
  }
}
