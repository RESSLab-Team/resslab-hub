<template>
  <double-chart
    label-prefix="connection."
    :searches.sync="fieldSearches"
    :fields="fields"
    :query="query"
    :type="type"
    :color="color"
    :promise="promise"
    :number-field="numberField"
    :range-promise="rangePromise"
  ></double-chart>
</template>

<script lang="ts">
import {
  ConnectionField,
  ConnectionNumberField,
  CountModel,
  RangeModel,
} from "@/backend";
import DoubleChartMixin from "@/components/commons/charts/DoubleChartMixin.vue";
import { AxiosResponse } from "axios";
import { Component } from "vue-property-decorator";

@Component
export default class ConnectionDoubleChart extends DoubleChartMixin<ConnectionField> {
  get promise(): Promise<AxiosResponse<CountModel[]>> {
    return this.$connectionsApi.getConnectionsCounts(this.fields, this.query);
  }

  get numberField(): ConnectionNumberField | undefined {
    const fieldString = this.fields[0].toString();
    return Object.values(ConnectionNumberField).find(
      (numberField) => fieldString === numberField.toString()
    );
  }

  get rangePromise(): Promise<AxiosResponse<RangeModel>> | undefined {
    if (this.numberField) {
      return this.$connectionsApi.getConnectionsRange(this.numberField);
    } else {
      return undefined;
    }
  }
}
</script>
