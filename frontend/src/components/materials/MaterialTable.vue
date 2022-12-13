<template>
  <simple-table
    :columns="columns"
    :get-counts="getCounts"
    :get-files="getFiles"
    :get-page="getPage"
    title="Material"
    prefix="material."
    :query="query"
    :search.sync="globalSearch"
    :searches.sync="materialSearches"
    @click="click"
    @loadPage="loadPage"
  >
  </simple-table>
</template>

<script lang="ts">
import {
  CountModel,
  ExtendedPageMaterialModel,
  MaterialField,
  MaterialModel,
} from "@/backend";
import SimpleTable, {
  Column,
  DownloadFile,
  DownloadType,
} from "@/components/commons/SimpleTable.vue";
import SimpleTableMixin from "@/components/commons/SimpleTableMixin.vue";
import { Searches } from "@/utils/common";
import { AxiosResponse } from "axios";
import { Component, Prop, PropSync } from "vue-property-decorator";

@Component({
  components: {
    SimpleTable,
  },
})
export default class MaterialTable extends SimpleTableMixin<MaterialModel> {
  @Prop({ default: "" })
  readonly query!: string;
  @PropSync("searches", { type: Object as () => Searches, default: () => ({}) })
  materialSearches!: Searches;
  @PropSync("search", { type: String, default: () => "" })
  globalSearch!: string;

  readonly columns: Column[] = [
    {
      value: MaterialField.ExperimentalProgram,
      type: "text",
    },
    {
      value: MaterialField.Id,
      type: "text",
    },
    {
      value: MaterialField.Type,
      type: "text",
    },
    {
      value: MaterialField.Profile,
      type: "text",
    },
    {
      value: MaterialField.Source,
      type: "text",
    },
  ];

  getCounts(): Promise<AxiosResponse<CountModel[]>> {
    return this.$materialsApi.getMaterialsCounts();
  }

  getPage(
    query?: string,
    sortBy?: Array<string>,
    sortDesc?: Array<boolean>,
    page?: number,
    size?: number
  ): Promise<AxiosResponse<ExtendedPageMaterialModel>> {
    return this.$materialsApi.getMaterials(query, sortBy, sortDesc, page, size);
  }

  getFiles(
    selectedItems: MaterialModel[],
    types: DownloadType[]
  ): Promise<DownloadFile[]> {
    const filePromises: Promise<DownloadFile>[] = [
      types.includes(DownloadType.Master)
        ? [
            this.$materialsApi
              .getMaterialsCsv(selectedItems.map((item) => item.id))
              .then((response) => ({
                filename: "materials.csv",
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
