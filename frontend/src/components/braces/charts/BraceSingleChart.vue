<template>
  <single-chart
    label-prefix="brace."
    :searches.sync="fieldSearches"
    :field="field"
    :query="query"
    :color="color"
    :promise="promise"
  >
  </single-chart>
</template>

<script lang="ts">
import { BraceField, CountModel } from "@/backend";
import SingleChartMixin from "@/components/commons/charts/SingleChartMixin.vue";
import { AxiosResponse } from "axios";
import { Component } from "vue-property-decorator";

@Component
export default class BraceSingleChart extends SingleChartMixin<BraceField> {
  get promise(): Promise<AxiosResponse<CountModel[]>> {
    return this.$bracesApi.getBracesCounts([this.field], this.query);
  }
}
</script>
