<template>
  <single-chart
    label-prefix="column."
    :searches.sync="fieldSearches"
    :field="field"
    :query="query"
    :color="color"
    :promise="promise"
  >
  </single-chart>
</template>

<script lang="ts">
import { ColumnField, CountModel } from "@/backend";
import SingleChartMixin from "@/components/commons/charts/SingleChartMixin.vue";
import { columnsApi } from "@/plugins/axios";
import { AxiosResponse } from "axios";
import { Component } from "vue-property-decorator";

@Component
export default class ColumnSingleChart extends SingleChartMixin<ColumnField> {
  get promise(): Promise<AxiosResponse<CountModel[]>> {
    return columnsApi.getColumnsCounts([this.field], this.query);
  }
}
</script>
