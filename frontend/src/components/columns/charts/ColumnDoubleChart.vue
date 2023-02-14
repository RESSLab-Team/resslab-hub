<template>
  <double-chart
    label-prefix="column."
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
  ColumnField,
  ColumnNumberField,
  CountModel,
  RangeModel,
} from "@/backend";
import DoubleChartMixin from "@/components/commons/charts/DoubleChartMixin.vue";
import { columnsApi } from "@/plugins/axios";
import { AxiosResponse } from "axios";
import { Component } from "vue-property-decorator";

@Component
export default class ColumnDoubleChart extends DoubleChartMixin<ColumnField> {
  get promise(): Promise<AxiosResponse<CountModel[]>> {
    return columnsApi.getColumnsCounts(this.requestFields, this.query);
  }

  get numberField(): ColumnNumberField | undefined {
    const fieldString = this.fields[0].toString();
    return Object.values(ColumnNumberField).find(
      (numberField) => fieldString === numberField.toString()
    );
  }

  get rangePromise(): Promise<RangeModel> | undefined {
    if (this.numberField) {
      return columnsApi
        .getColumnsRange(this.numberField)
        .then((response) => response.data);
    } else {
      return undefined;
    }
  }
}
</script>
