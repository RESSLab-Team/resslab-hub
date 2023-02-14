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
      Columns
      <info-tooltip>
        <p>
          The Columns Database presents data from early 1970s on columns under
          reversed cyclic and monotonic loading. The primary data involve the
          deduced moment chord rotation of the column and deduced column axial
          shortening versus chord rotation.
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
import SimpleTableMixin from "@/components/commons/SimpleTableMixin.vue";
import { columnsApi } from "@/plugins/axios";
import { Searches } from "@/utils/common";
import { AxiosResponse } from "axios";
import { Component, Prop, PropSync } from "vue-property-decorator";

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
    return columnsApi.getColumnsCounts();
  }

  getPage(
    query?: string,
    sortBy?: Array<string>,
    sortDesc?: Array<boolean>,
    page?: number,
    size?: number
  ): Promise<AxiosResponse<ExtendedPageColumnModel>> {
    return columnsApi.getColumns(query, sortBy, sortDesc, page, size);
  }

  getFiles(
    selectedItems: ColumnModel[],
    types: DownloadType[]
  ): Promise<DownloadFile[]> {
    return this.getDownloadFiles(
      selectedItems,
      types,
      "column",
      (ids) => columnsApi.getColumnsCsv(ids),
      {
        name: "axial-shortening",
        countKey: "axial_shortening_count",
        getCsv: (id) => columnsApi.getColumnsAxialShorteningCsv(id),
      },
      {
        name: "moment-strong",
        countKey: "moment_strong_count",
        getCsv: (id) => columnsApi.getColumnsMomentStrongCsv(id),
      },
      {
        name: "moment-weak",
        countKey: "moment_weak_count",
        getCsv: (id) => columnsApi.getColumnsMomentWeakCsv(id),
      }
    );
  }
}
</script>
