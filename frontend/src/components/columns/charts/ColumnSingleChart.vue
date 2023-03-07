<script setup lang="ts">
import { ColumnField } from "@/backend";
import { columnsApi } from "@/plugins/axios";
import { defineProps, toRef, defineEmits } from "vue";
import {
  ChartEmits,
  singleChartProps,
  useSingleChart,
} from "@/composables/chart";
import SingleChart from "@/components/commons/charts/SingleChart.vue";

const props = defineProps(singleChartProps<ColumnField>());
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>();

const { counts, changeSearches } = useSingleChart<ColumnField>(
  emit,
  props.field,
  toRef(props, "query"),
  (fields, query) => columnsApi.getColumnsCounts(fields, query)
);
</script>

<template>
  <single-chart
    :color="color"
    :counts="counts"
    :field="field"
    label-prefix="column."
    @change:searches="changeSearches"
  />
</template>
