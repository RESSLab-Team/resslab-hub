<template>
  <simple-parallel-chart
    label-prefix="material."
    :id-field="idField"
    :searches.sync="fieldSearches"
    :fields="fields"
    :query="query"
    :color="color"
    :get-matrix="getMatrix"
  ></simple-parallel-chart>
</template>

<script lang="ts">
import { MaterialField, MatrixModel } from "@/backend";
import SimpleParallelChartMixin from "@/components/commons/charts/SimpleParallelChartMixin.vue";
import { materialsApi } from "@/plugins/axios";
import { AxiosResponse } from "axios";
import { Component } from "vue-property-decorator";

@Component
export default class MaterialParallelChart extends SimpleParallelChartMixin<MaterialField> {
  readonly idField = MaterialField.Id;

  getMatrix(fields: MaterialField[]): Promise<AxiosResponse<MatrixModel>> {
    return materialsApi.getMaterialsMatrix(fields, this.query);
  }
}
</script>
