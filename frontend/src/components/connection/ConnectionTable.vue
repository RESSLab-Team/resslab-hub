<template>
  <simple-table
    :columns="columns"
    :get-counts="getCounts"
    :get-files="getFiles"
    :get-page="getPage"
    title="Connections"
    prefix="connection."
    :query="query"
    :search.sync="globalSearch"
    :searches.sync="columnSearches"
    @click="click"
  >
    <template
      v-slot:[`column.header.item.connection_type`]="{ item, on, attrs }"
    >
      <v-list-item #default="{ active }" v-bind="attrs" v-on="on">
        <v-list-item-action>
          <v-checkbox :input-value="active"></v-checkbox>
        </v-list-item-action>
        <v-img
          contain
          max-height="128"
          max-width="128"
          :src="getImageSource(item)"
        ></v-img>
        {{ item }}
      </v-list-item>
    </template>
  </simple-table>
</template>

<script lang="ts">
import {
  ConnectionModel,
  CountModel,
  ExtendedPageConnectionModel,
} from "@/backend";
import SimpleTable, {
  Column,
  DownloadFile,
  DownloadType,
} from "@/components/commons/SimpleTable.vue";
import { publicPath, Searches } from "@/utils/common";
import { AxiosResponse } from "axios";
import { Component, Prop, PropSync, Vue } from "vue-property-decorator";

@Component({
  components: {
    SimpleTable,
  },
})
export default class ConnectionTable extends Vue {
  @Prop({ default: "" })
  readonly query!: string;
  @PropSync("searches", { type: Object as () => Searches, default: () => ({}) })
  columnSearches!: Searches;
  @PropSync("search", { type: String, default: () => "" })
  globalSearch!: string;

  readonly columns: Column[] = [
    {
      value: "experimental_program",
      type: "text",
    },
    {
      value: "date",
      type: "number",
      filterOnly: true,
    },
    {
      value: "specimen_designation",
      type: "text",
    },
    {
      value: "northridge",
      type: "option",
      options: ["pre", "post"],
      filterOnly: true,
    },
    {
      value: "specimen_type",
      type: "text",
      options: ["exterior%", "interior%"],
      filterOnly: true,
    },
    {
      value: "slab",
      type: "boolean",
      filterOnly: true,
    },
    {
      value: "connection_type",
      type: "option",
      options: ["WUF-W", "RBS", "WUF-B", "BFP", "WFP", "KBB", "BEEP"],
    },
    {
      value: "section_b",
      type: "text",
    },
    {
      value: "section_c",
      type: "text",
    },
    {
      value: "n_dp",
      type: "number",
      options: ["0", "> 0"],
      filterOnly: true,
    },
    {
      value: "t_dp_tot",
      type: "number",
    },
  ];

  getCounts(): Promise<AxiosResponse<CountModel[]>> {
    return this.$connectionsApi.getCounts();
  }

  getPage(
    query?: string,
    sortBy?: Array<string>,
    sortDesc?: Array<boolean>,
    page?: number,
    size?: number
  ): Promise<AxiosResponse<ExtendedPageConnectionModel>> {
    return this.$connectionsApi.getConnections(
      query,
      sortBy,
      sortDesc,
      page,
      size
    );
  }

  click(connection: ConnectionModel): void {
    this.$emit("click", connection);
  }

  getFiles(
    selectedItems: ConnectionModel[],
    types: DownloadType[]
  ): Promise<DownloadFile[]> {
    const filePromises: Promise<DownloadFile>[] = [
      types.includes(DownloadType.Master)
        ? [
            this.$connectionsApi
              .getCsv(selectedItems.map((item) => item.id))
              .then((response) => ({
                filename: "connections.csv",
                content: response.data as unknown as string,
              })),
          ]
        : [],
      types.includes(DownloadType.Test)
        ? [
            ...selectedItems
              .filter((item) => item.global_count > 0)
              .map((item) => item.id)
              .map((id) =>
                this.$connectionsApi.getGlobalCsv(id).then((response) => ({
                  filename: `connection-global-${id}.csv`,
                  content: response.data as unknown as string,
                }))
              ),
            ...selectedItems
              .filter((item) => item.global_west_count > 0)
              .map((item) => item.id)
              .map((id) =>
                this.$connectionsApi.getGlobalWestCsv(id).then((response) => ({
                  filename: `connection-global-west-${id}.csv`,
                  content: response.data as unknown as string,
                }))
              ),
            ...selectedItems
              .filter((item) => item.panel_zone_count > 0)
              .map((item) => item.id)
              .map((id) =>
                this.$connectionsApi.getPanelZonesCsv(id).then((response) => ({
                  filename: `connection-panel-zone-${id}.csv`,
                  content: response.data as unknown as string,
                }))
              ),
          ]
        : [],
    ].flat();
    return Promise.all(filePromises);
  }

  getImageSource(item: string): string {
    return publicPath + "img/connection-type/" + item.toLowerCase() + ".png";
  }
}
</script>
