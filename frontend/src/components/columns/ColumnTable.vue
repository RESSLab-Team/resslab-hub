<template>
  <simple-table
    :columns="columns"
    :get-counts="getCounts"
    :get-files="getFiles"
    :get-page="getPage"
    title="Column"
    prefix="column."
    :query="query"
    :search.sync="globalSearch"
    :searches.sync="columnSearches"
    @click="click"
  >
  </simple-table>
</template>

<script lang="ts">
import {
  ColumnField,
  ColumnModel,
  CountModel,
  ExtendedPageColumnModel,
} from "@/backend";
import SimpleTable, {
  Column,
  DownloadFile,
  DownloadType,
} from "@/components/commons/SimpleTable.vue";
import { Searches } from "@/utils/common";
import { AxiosResponse } from "axios";
import { Component, Prop, PropSync, Vue } from "vue-property-decorator";

@Component({
  components: {
    SimpleTable,
  },
})
export default class ColumnTable extends Vue {
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

  click(item: ColumnModel): void {
    this.$emit("click", item);
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
