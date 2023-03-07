<script setup lang="ts">
import { ColumnField } from "@/backend";
import {
  ChartEmits,
  parallelChartProps,
  useParallelChart,
} from "@/composables/chart";
import { columnsApi } from "@/plugins/axios";
import { defineProps, defineEmits, toRef } from "vue";
import SimpleParallelChart from "@/components/commons/charts/SimpleParallelChart.vue";

const props = defineProps(parallelChartProps<ColumnField>());
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>();

const { changeSearches, data, ids, requestFields } =
  useParallelChart<ColumnField>(
    emit,
    ColumnField.Id,
    props.fields,
    toRef(props, "query"),
    (fields, query) => columnsApi.getColumnsMatrix(fields, query)
  );
</script>

<template>
  <simple-parallel-chart
    :color="color"
    :data="data"
    :fields="fields"
    :ids="ids"
    label-prefix="column."
    :request-fields="requestFields"
    @change:searches="changeSearches"
  />
</template>
