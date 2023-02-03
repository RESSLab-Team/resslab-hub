<template>
  <simple-table
    :columns="columns"
    :get-counts="getCounts"
    :get-files="getFiles"
    :get-page="getPage"
    prefix="brace."
    :query="query"
    :search.sync="globalSearch"
    :searches.sync="braceSearches"
    @click="click"
    @loadPage="loadPage"
  >
    <template #title>
      Brace
      <info-tooltip>
        <p>
          The Brace Database presents data from mid 1970s on steel braces of
          various configurations. The braces are subjected to monotonic,
          symmetric cyclic and other loading histories. The primary data involve
          the brace axial load versus axial displacement.
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
  BraceField,
  BraceModel,
  CountModel,
  ExtendedPageBraceModel,
} from "@/backend";
import InfoTooltip from "@/components/commons/InfoTooltip.vue";
import SimpleTable, {
  Column,
  DownloadFile,
  DownloadType,
} from "@/components/commons/SimpleTable.vue";
import SimpleTableMixin from "@/components/commons/SimpleTableMixin.vue";
import { bracesApi } from "@/plugins/axios";
import { Searches } from "@/utils/common";
import { AxiosResponse } from "axios";
import { Component, Prop, PropSync } from "vue-property-decorator";

@Component({
  components: {
    SimpleTable,
    InfoTooltip,
  },
})
export default class BraceTable extends SimpleTableMixin<BraceModel> {
  @Prop({ default: "" })
  readonly query!: string;
  @PropSync("searches", { type: Object as () => Searches, default: () => ({}) })
  braceSearches!: Searches;
  @PropSync("search", { type: String, default: () => "" })
  globalSearch!: string;

  readonly columns: Column[] = [
    {
      value: BraceField.Investigator,
      type: "text",
    },
    {
      value: BraceField.SpecimenId,
      type: "text",
    },
    {
      value: BraceField.CrossSectionSize,
      type: "text",
    },
    {
      value: BraceField.Steel,
      type: "text",
    },
    {
      value: BraceField.KlR,
      type: "number",
    },
  ];

  getCounts(): Promise<AxiosResponse<CountModel[]>> {
    return bracesApi.getBracesCounts();
  }

  getPage(
    query?: string,
    sortBy?: Array<string>,
    sortDesc?: Array<boolean>,
    page?: number,
    size?: number
  ): Promise<AxiosResponse<ExtendedPageBraceModel>> {
    return bracesApi.getBraces(query, sortBy, sortDesc, page, size);
  }

  getFiles(
    selectedItems: BraceModel[],
    types: DownloadType[]
  ): Promise<DownloadFile[]> {
    return this.getDownloadFiles(
      selectedItems,
      types,
      "brace",
      (ids) => bracesApi.getBracesCsv(ids),
      {
        name: "displacement",
        countKey: "displacement_count",
        getCsv: (id) => bracesApi.getBracesDisplacementCsv(id),
      }
    );
  }
}
</script>
