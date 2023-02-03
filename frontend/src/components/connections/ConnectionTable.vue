<template>
  <simple-table
    :columns="columns"
    :get-counts="getCounts"
    :get-files="getFiles"
    :get-page="getPage"
    prefix="connection."
    :query="query"
    :search.sync="globalSearch"
    :searches.sync="columnSearches"
    @click="click"
    @loadPage="loadPage"
  >
    <template #title>
      Connections
      <info-tooltip>
        <p>
          The Connections Database presents data from early 1970s on
          beam-to-column connections under reversed cyclic and monotonic
          loading. The primary data involve the global behavior of the
          connection and the decomposed panel zone shear versus shear
          distortion, deduced beam end moment versus chord rotation, whenever
          available.
        </p>
        How to use?
        <ul>
          <li>
            Filter the table by making selections in the various plots around
            the table, or by using the filters and dropdowns above the table
            headers.
          </li>
          <li>Click on a row to see the data of a single test.</li>
          <li>
            Download specific tests results by selecting the test (left-most
            column) and click "Download" below.
          </li>
          <li>
            Share specific tests results by selecting the test (left-most
            column) and click "Share" below.
          </li>
        </ul>
      </info-tooltip>
    </template>
    <template #[`column.header.item.connection_type`]="{ item, on, attrs }">
      <v-list-item v-slot="{ active }" v-bind="attrs" v-on="on">
        <v-list-item-action>
          <v-checkbox :input-value="active"></v-checkbox>
        </v-list-item-action>
        <v-img
          contain
          max-height="128"
          max-width="128"
          :src="getImageSource(item)"
        />
        <span class="ma-2">{{ item }}</span>
      </v-list-item>
    </template>
  </simple-table>
</template>

<script lang="ts">
import {
  ConnectionField,
  ConnectionModel,
  CountModel,
  ExtendedPageConnectionModel,
} from "@/backend";
import InfoTooltip from "@/components/commons/InfoTooltip.vue";
import SimpleTable, {
  Column,
  DownloadFile,
  DownloadType,
} from "@/components/commons/SimpleTable.vue";
import SimpleTableMixin from "@/components/commons/SimpleTableMixin.vue";
import { publicPath, Searches } from "@/utils/common";
import { AxiosResponse } from "axios";
import { Component, Prop, PropSync } from "vue-property-decorator";

@Component({
  components: {
    InfoTooltip,
    SimpleTable,
  },
})
export default class ConnectionTable extends SimpleTableMixin<ConnectionModel> {
  @Prop({ default: "" })
  readonly query!: string;
  @PropSync("searches", { type: Object as () => Searches, default: () => ({}) })
  columnSearches!: Searches;
  @PropSync("search", { type: String, default: () => "" })
  globalSearch!: string;

  readonly columns: Column[] = [
    {
      value: ConnectionField.ExperimentalProgram,
      type: "text",
    },
    {
      value: ConnectionField.Date,
      type: "number",
      filterOnly: true,
    },
    {
      value: ConnectionField.SpecimenDesignation,
      type: "text",
    },
    {
      value: ConnectionField.Northridge,
      type: "option",
      options: ["pre", "post"],
      filterOnly: true,
    },
    {
      value: ConnectionField.SpecimenType,
      type: "text",
      options: ["exterior%", "interior%"],
      filterOnly: true,
    },
    {
      value: ConnectionField.Slab,
      type: "boolean",
      filterOnly: true,
    },
    {
      value: ConnectionField.ConnectionType,
      type: "option",
      options: ["WUF-W", "RBS", "WUF-B", "BFP", "WFP", "KBB", "BEEP"],
    },
    {
      value: ConnectionField.SectionB,
      type: "text",
    },
    {
      value: ConnectionField.SectionC,
      type: "text",
    },
    {
      value: ConnectionField.NDp,
      type: "number",
      options: ["0", "> 0"],
      filterOnly: true,
    },
    {
      value: ConnectionField.TDpTot,
      type: "number",
    },
  ];

  getCounts(): Promise<AxiosResponse<CountModel[]>> {
    return this.$connectionsApi.getConnectionsCounts();
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

  getFiles(
    selectedItems: ConnectionModel[],
    types: DownloadType[]
  ): Promise<DownloadFile[]> {
    const filePromises: Promise<DownloadFile>[] = [
      types.includes(DownloadType.Master)
        ? [
            this.$connectionsApi
              .getConnectionsCsv(selectedItems.map((item) => item.id))
              .then((response) => ({
                filename: "connections.csv",
                content: response.data as unknown as string,
              })),
          ]
        : [],
      types.includes(DownloadType.Test)
        ? [
            ...selectedItems
              .filter((item) => item.beam_count > 0)
              .map((item) => item.id)
              .map((id) =>
                this.$connectionsApi
                  .getConnectionsBeamCsv(id)
                  .then((response) => ({
                    filename: `connection-beam-${id}.csv`,
                    content: response.data as unknown as string,
                  }))
              ),
            ...selectedItems
              .filter((item) => item.beam_west_count > 0)
              .map((item) => item.id)
              .map((id) =>
                this.$connectionsApi
                  .getConnectionsBeamWestCsv(id)
                  .then((response) => ({
                    filename: `connection-beam-west-${id}.csv`,
                    content: response.data as unknown as string,
                  }))
              ),
            ...selectedItems
              .filter((item) => item.global_count > 0)
              .map((item) => item.id)
              .map((id) =>
                this.$connectionsApi
                  .getConnectionsGlobalCsv(id)
                  .then((response) => ({
                    filename: `connection-global-${id}.csv`,
                    content: response.data as unknown as string,
                  }))
              ),
            ...selectedItems
              .filter((item) => item.global_west_count > 0)
              .map((item) => item.id)
              .map((id) =>
                this.$connectionsApi
                  .getConnectionsGlobalWestCsv(id)
                  .then((response) => ({
                    filename: `connection-global-west-${id}.csv`,
                    content: response.data as unknown as string,
                  }))
              ),
            ...selectedItems
              .filter((item) => item.panel_zone_count > 0)
              .map((item) => item.id)
              .map((id) =>
                this.$connectionsApi
                  .getConnectionsPanelZonesCsv(id)
                  .then((response) => ({
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
    return publicPath + "img/connection-type/" + item.toLowerCase() + ".svg";
  }
}
</script>
