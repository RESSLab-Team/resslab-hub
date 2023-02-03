<template>
  <simple-parallel-chart
    label-prefix="brace."
    :id-field="idField"
    :searches.sync="fieldSearches"
    :fields="fields"
    :query="query"
    :color="color"
    :get-matrix="getMatrix"
  ></simple-parallel-chart>
</template>

<script lang="ts">
import { BraceField, MatrixModel } from "@/backend";
import SimpleParallelChartMixin from "@/components/commons/charts/SimpleParallelChartMixin.vue";
import { bracesApi } from "@/plugins/axios";
import { AxiosResponse } from "axios";
import { Component } from "vue-property-decorator";

@Component
export default class BraceParallelChart extends SimpleParallelChartMixin<BraceField> {
  readonly idField = BraceField.Id;

  getMatrix(fields: BraceField[]): Promise<AxiosResponse<MatrixModel>> {
    return bracesApi.getBracesMatrix(fields, this.query);
  }
}
</script>
