<template>
  <simple-table
    :columns="columns"
    :get-counts="getCounts"
    :get-files="getFiles"
    :get-page="getPage"
    prefix="column."
    :query="query"
    :search.sync="globalSearch"
    :searches.sync="columnSearches"
    @click="click"
    @loadPage="loadPage"
  >
    <template #title>
      Column
      <info-tooltip>
        <p>
          The Columns Database presents data from early 1970s on beam-to-column
          columns under reversed cyclic and monotonic loading. The primary data
          involve the global behavior of the column and the decomposed panel
          zone shear versus shear distortion, deduced beam end moment versus
          chord rotation, whenever available.
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
  </simple-table>
</template>

<script lang="ts">
import {
  ColumnField,
  ColumnModel,
  CountModel,
  ExtendedPageColumnModel,
} from "@/backend";
import InfoTooltip from "@/components/commons/InfoTooltip.vue";
import SimpleTable, {
  Column,
  DownloadFile,
  DownloadType,
} from "@/components/commons/SimpleTable.vue";
import { Searches } from "@/utils/common";
import { AxiosResponse } from "axios";
import { Component, Prop, PropSync } from "vue-property-decorator";
import SimpleTableMixin from "@/components/commons/SimpleTableMixin.vue";

@Component({
  components: {
    InfoTooltip,
    SimpleTable,
  },
})
export default class ColumnTable extends SimpleTableMixin<ColumnModel> {
  @Prop({ default: "" })
  readonly query!: string;
  @PropSync("searches", { type: Object as () => Searches, default: () => ({}) })
  columnSearches!: Searches;
  @PropSync("search", { type: String, default: () => "" })
  globalSearch!: string;

  readonly columns: Column[] = [
    {
      value: ColumnField.ExperimentalProgram,
      type: "text",
    },
    {
      value: ColumnField.SpecimenDesignation,
      type: "text",
    },
    {
      value: ColumnField.SectionC,
      type: "text",
    },
    {
      value: ColumnField.PGOverPYm,
      type: "number",
    },
    {
      value: ColumnField.LBOverRYc,
      type: "number",
    },
    {
      value: ColumnField.DirectionLp,
      type: "text",
    },
  ];

  getCounts(): Promise<AxiosResponse<CountModel[]>> {
    return this.$columnsApi.getColumnsCounts();
  }

  getPage(
    query?: string,
    sortBy?: Array<string>,
    sortDesc?: Array<boolean>,
    page?: number,
    size?: number
  ): Promise<AxiosResponse<ExtendedPageColumnModel>> {
    return this.$columnsApi.getColumns(query, sortBy, sortDesc, page, size);
  }

  getFiles(
    selectedItems: ColumnModel[],
    types: DownloadType[]
  ): Promise<DownloadFile[]> {
    const filePromises: Promise<DownloadFile>[] = [
      types.includes(DownloadType.Master)
        ? [
            this.$columnsApi
              .getColumnsCsv(selectedItems.map((item) => item.id))
              .then((response) => ({
                filename: "columns.csv",
                content: response.data as unknown as string,
              })),
          ]
        : [],
      types.includes(DownloadType.Test)
        ? [
            // TODO
          ]
        : [],
    ].flat();
    return Promise.all(filePromises);
  }
}
</script>
