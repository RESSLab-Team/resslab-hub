<script setup lang="ts">
import { ColumnField, ColumnNumberField } from "@/backend";
import { columnsApi } from "@/plugins/axios";
import { defineProps, defineEmits, toRef } from "vue";
import {
  ChartEmits,
  doubleChartProps,
  useDoubleChart,
} from "@/composables/chart";
import DoubleChart from "@/components/commons/charts/DoubleChart.vue";

const props = defineProps(doubleChartProps<ColumnField>());
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>();

const {
  counts,
  changeSearches,
  dateMax,
  dateMin,
  dateRange,
  numberMax,
  numberMin,
  numberRange,
} = useDoubleChart<ColumnField, ColumnNumberField>(
  emit,
  props.fields,
  toRef(props, "query"),
  (fields, query) => columnsApi.getColumnsCounts(fields, query),
  {
    field: ColumnNumberField,
    getRange: (field) => columnsApi.getColumnsRange(field),
  }
);
</script>

<template>
  <double-chart
    :color="color"
    :counts="counts"
    :date-max="dateMax"
    :date-min="dateMin"
    :date-range.sync="dateRange"
    :fields="fields"
    label-prefix="column."
    :number-max="numberMax"
    :number-min="numberMin"
    :number-range.sync="numberRange"
    :type="props.type"
    @change:searches="changeSearches"
  />
</template>
