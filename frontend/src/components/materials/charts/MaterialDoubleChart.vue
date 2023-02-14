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
    :date-range-promise="dateRangePromise"
    :date="!!dateField"
  />
</template>

<script lang="ts">
import {
  CountModel,
  DateRangeModel,
  MaterialDateField,
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

  get fieldString(): string {
    return this.fields[0].toString();
  }

  get numberField(): MaterialNumberField | undefined {
    return Object.values(MaterialNumberField).find(
      (numberField) => this.fieldString === numberField.toString()
    );
  }

  get dateField(): MaterialDateField | undefined {
    return Object.values(MaterialDateField).find(
      (numberField) => this.fieldString === numberField.toString()
    );
  }

  get rangePromise(): Promise<RangeModel> | undefined {
    if (this.numberField) {
      return materialsApi
        .getMaterialsRange(this.numberField)
        .then((response) => response.data);
    }
    return undefined;
  }

  get dateRangePromise(): Promise<DateRangeModel> | undefined {
    if (this.dateField) {
      return materialsApi
        .getMaterialsDateRange(this.dateField)
        .then((response) => response.data);
    }
    return undefined;
  }
}
</script>
