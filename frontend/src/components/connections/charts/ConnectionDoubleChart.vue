<script setup lang="ts">
import { ConnectionField, ConnectionNumberField } from "@/backend";
import { connectionsApi } from "@/plugins/axios";
import { defineProps, defineEmits, toRef } from "vue";
import DoubleChart from "@/components/commons/charts/DoubleChart.vue";
import {
  ChartEmits,
  doubleChartProps,
  useDoubleChart,
} from "@/composables/chart";

const props = defineProps(doubleChartProps<ConnectionField>());
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
} = useDoubleChart<ConnectionField, ConnectionNumberField>(
  emit,
  props.fields,
  toRef(props, "query"),
  (fields, query) => connectionsApi.getConnectionsCounts(fields, query),
  {
    field: ConnectionNumberField,
    getRange: (field) => connectionsApi.getConnectionsRange(field),
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
    label-prefix="connection."
    :number-max="numberMax"
    :number-min="numberMin"
    :number-range.sync="numberRange"
    :type="props.type"
    @change:searches="changeSearches"
  />
</template>
