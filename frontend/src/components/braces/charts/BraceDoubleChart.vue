<script setup lang="ts">
import { BraceField, BraceNumberField } from "@/backend";
import {
  ChartEmits,
  doubleChartProps,
  useDoubleChart,
} from "@/composables/chart";
import { bracesApi } from "@/plugins/axios";
import { defineProps, defineEmits, toRef } from "vue";
import DoubleChart from "@/components/commons/charts/DoubleChart.vue";

const props = defineProps(doubleChartProps<BraceField>());
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
} = useDoubleChart<BraceField, BraceNumberField>(
  emit,
  props.fields,
  toRef(props, "query"),
  (fields, query) => bracesApi.getBracesCounts(fields, query),
  {
    field: BraceNumberField,
    getRange: (field) => bracesApi.getBracesRange(field),
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
    label-prefix="brace."
    :number-max="numberMax"
    :number-min="numberMin"
    :number-range.sync="numberRange"
    :type="props.type"
    @change:searches="changeSearches"
  />
</template>
