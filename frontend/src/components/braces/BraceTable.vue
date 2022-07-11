<template>
  <simple-table
    :columns="columns"
    :get-counts="getCounts"
    :get-files="getFiles"
    :get-page="getPage"
    title="Brace"
    prefix="brace."
    :query="query"
    :search.sync="globalSearch"
    :searches.sync="braceSearches"
    @click="click"
  >
  </simple-table>
</template>

<script lang="ts">
import {
  BraceField,
  BraceModel,
  CountModel,
  ExtendedPageBraceModel,
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
export default class BraceTable extends Vue {
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
      value: BraceField.CrossSectionShape,
      type: "text",
    },
    {
      value: BraceField.CrossSectionSize,
      type: "text",
    },
    {
      value: BraceField.Area,
      type: "number",
    },
  ];

  getCounts(): Promise<AxiosResponse<CountModel[]>> {
    return this.$bracesApi.getBracesCounts();
  }

  getPage(
    query?: string,
    sortBy?: Array<string>,
    sortDesc?: Array<boolean>,
    page?: number,
    size?: number
  ): Promise<AxiosResponse<ExtendedPageBraceModel>> {
    return this.$bracesApi.getBraces(query, sortBy, sortDesc, page, size);
  }

  click(item: BraceModel): void {
    this.$emit("click", item);
  }

  getFiles(
    selectedItems: BraceModel[],
    types: DownloadType[]
  ): Promise<DownloadFile[]> {
    const filePromises: Promise<DownloadFile>[] = [
      types.includes(DownloadType.Master)
        ? [
            this.$bracesApi
              .getBracesCsv(selectedItems.map((item) => item.id))
              .then((response) => ({
                filename: "braces.csv",
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
