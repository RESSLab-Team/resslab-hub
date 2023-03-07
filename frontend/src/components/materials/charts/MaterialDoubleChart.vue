<script setup lang="ts">
import {
  MaterialDateField,
  MaterialField,
  MaterialNumberField,
} from "@/backend";
import { materialsApi } from "@/plugins/axios";
import { defineProps, defineEmits, toRef } from "vue";
import DoubleChart from "@/components/commons/charts/DoubleChart.vue";
import {
  ChartEmits,
  doubleChartProps,
  useDoubleChart,
} from "@/composables/chart";

const props = defineProps(doubleChartProps<MaterialField>());
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
} = useDoubleChart<MaterialField, MaterialNumberField, MaterialDateField>(
  emit,
  props.fields,
  toRef(props, "query"),
  (fields, query) => materialsApi.getMaterialsCounts(fields, query),
  {
    field: MaterialNumberField,
    getRange: (field) => materialsApi.getMaterialsRange(field),
  },
  {
    field: MaterialDateField,
    getRange: (field) => materialsApi.getMaterialsDateRange(field),
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
    label-prefix="material."
    :number-max="numberMax"
    :number-min="numberMin"
    :number-range.sync="numberRange"
    :type="props.type"
    @change:searches="changeSearches"
  />
</template>
