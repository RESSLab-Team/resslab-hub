<template>
  <double-chart
    label-prefix="brace."
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
  BraceField,
  BraceNumberField,
  CountModel,
  RangeModel,
} from "@/backend";
import DoubleChartMixin from "@/components/commons/charts/DoubleChartMixin.vue";
import { bracesApi } from "@/plugins/axios";
import { AxiosResponse } from "axios";
import { Component } from "vue-property-decorator";

@Component
export default class BraceDoubleChart extends DoubleChartMixin<BraceField> {
  get promise(): Promise<AxiosResponse<CountModel[]>> {
    return bracesApi.getBracesCounts(this.requestFields, this.query);
  }

  get numberField(): BraceNumberField | undefined {
    const fieldString = this.fields[0].toString();
    return Object.values(BraceNumberField).find(
      (numberField) => fieldString === numberField.toString()
    );
  }

  get rangePromise(): Promise<RangeModel> | undefined {
    if (this.numberField) {
      return bracesApi
        .getBracesRange(this.numberField)
        .then((response) => response.data);
    } else {
      return undefined;
    }
  }
}
</script>
