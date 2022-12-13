import { BracesApi, ColumnsApi, ConnectionsApi, MaterialsApi } from "@/backend";

declare module "vue/types/vue" {
  interface Vue {
    $bracesApi: BracesApi;
    $columnsApi: ColumnsApi;
    $connectionsApi: ConnectionsApi;
    $materialsApi: MaterialsApi;
  }
}
