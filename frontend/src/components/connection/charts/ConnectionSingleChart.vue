<template>
  <single-chart
    label-prefix="connection."
    :searches.sync="fieldSearches"
    :field="field"
    :query="query"
    :color="color"
    :promise="promise"
    @mouseover="mouseover"
    @mouseout="mouseout"
  >
    <template v-slot>
      <v-img
        v-if="imageUrl"
        aspect-ratio="3"
        contain
        :src="imageUrl"
        min-height="120"
      ></v-img>
    </template>
  </single-chart>
</template>

<script lang="ts">
import { ConnectionField, CountModel } from "@/backend";
import SingleChartMixin from "@/components/commons/charts/SingleChartMixin.vue";
import { publicPath } from "@/utils/common";
import { AxiosResponse } from "axios";
import { CallbackDataParams } from "echarts/types/dist/shared";
import { Component } from "vue-property-decorator";

@Component
export default class ConnectionSingleChart extends SingleChartMixin<ConnectionField> {
  imageUrl = "";

  get promise(): Promise<AxiosResponse<CountModel[]>> {
    return this.$connectionsApi.getConnectionsCounts([this.field], this.query);
  }

  mouseover(params: CallbackDataParams): void {
    if (this.field === ConnectionField.ConnectionType) {
      const name: string = params.name.toLowerCase();
      this.imageUrl = publicPath + "img/connection-type/" + name + ".png";
    }
  }

  mouseout(): void {
    this.imageUrl = "";
  }
}
</script>
