<template>
  <simple-parallel-chart
    label-prefix="column."
    :id-field="idField"
    :searches.sync="fieldSearches"
    :fields="fields"
    :query="query"
    :color="color"
    :get-matrix="getMatrix"
  ></simple-parallel-chart>
</template>

<script lang="ts">
import { ColumnField, MatrixModel } from "@/backend";
import SimpleParallelChartMixin from "@/components/commons/charts/SimpleParallelChartMixin.vue";
import { AxiosResponse } from "axios";
import { Component } from "vue-property-decorator";

@Component
export default class ColumnParallelChart extends SimpleParallelChartMixin<ColumnField> {
  readonly idField = ColumnField.Id;

  getMatrix(fields: ColumnField[]): Promise<AxiosResponse<MatrixModel>> {
    return this.$columnsApi.getColumnsMatrix(fields, this.query);
  }
}
</script>
