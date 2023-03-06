<template>
  <simple-parallel-chart
    label-prefix="connection."
    :id-field="idField"
    :searches.sync="fieldSearches"
    :fields="fields"
    :query="query"
    :color="color"
    :get-matrix="getMatrix"
  >
    <template #title>
      <slot name="title" />
    </template>
  </simple-parallel-chart>
</template>

<script lang="ts">
import { ConnectionField, MatrixModel } from "@/backend";
import SimpleParallelChartMixin from "@/components/commons/charts/SimpleParallelChartMixin.vue";
import { connectionsApi } from "@/plugins/axios";
import { AxiosResponse } from "axios";
import { Component } from "vue-property-decorator";

@Component
export default class ConnectionParallelChart extends SimpleParallelChartMixin<ConnectionField> {
  readonly idField = ConnectionField.Id;

  getMatrix(fields: ConnectionField[]): Promise<AxiosResponse<MatrixModel>> {
    return connectionsApi.getConnectionsMatrix(fields, this.query);
  }
}
</script>
