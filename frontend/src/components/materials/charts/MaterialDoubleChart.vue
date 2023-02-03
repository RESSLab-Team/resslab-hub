<template>
  <double-chart
    label-prefix="material."
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
  CountModel,
  MaterialField,
  MaterialNumberField,
  RangeModel,
} from "@/backend";
import DoubleChartMixin from "@/components/commons/charts/DoubleChartMixin.vue";
import { materialsApi } from "@/plugins/axios";
import { AxiosResponse } from "axios";
import { Component } from "vue-property-decorator";

@Component
export default class MaterialDoubleChart extends DoubleChartMixin<MaterialField> {
  get promise(): Promise<AxiosResponse<CountModel[]>> {
    return materialsApi.getMaterialsCounts(this.requestFields, this.query);
  }

  get numberField(): MaterialNumberField | undefined {
    const fieldString = this.fields[0].toString();
    return Object.values(MaterialNumberField).find(
      (numberField) => fieldString === numberField.toString()
    );
  }

  get rangePromise(): Promise<AxiosResponse<RangeModel>> | undefined {
    if (this.numberField) {
      return materialsApi.getMaterialsRange(this.numberField);
    } else {
      return undefined;
    }
  }
}
</script>
