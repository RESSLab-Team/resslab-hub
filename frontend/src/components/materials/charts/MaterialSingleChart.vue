<template>
  <single-chart
    label-prefix="material."
    :searches.sync="fieldSearches"
    :field="field"
    :query="query"
    :color="color"
    :promise="promise"
  >
  </single-chart>
</template>

<script lang="ts">
import { CountModel, MaterialField } from "@/backend";
import SingleChartMixin from "@/components/commons/charts/SingleChartMixin.vue";
import { materialsApi } from "@/plugins/axios";
import { AxiosResponse } from "axios";
import { Component } from "vue-property-decorator";

@Component
export default class MaterialSingleChart extends SingleChartMixin<MaterialField> {
  get promise(): Promise<AxiosResponse<CountModel[]>> {
    return materialsApi.getMaterialsCounts([this.field], this.query);
  }
}
</script>
