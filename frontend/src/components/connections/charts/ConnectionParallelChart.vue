<script setup lang="ts">
import { ConnectionField } from "@/backend";
import { connectionsApi } from "@/plugins/axios";
import { defineProps, defineEmits, toRef } from "vue";
import {
  ChartEmits,
  parallelChartProps,
  useParallelChart,
} from "@/composables/chart";
import SimpleParallelChart from "@/components/commons/charts/SimpleParallelChart.vue";

const props = defineProps(parallelChartProps<ConnectionField>());
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>();

const { changeSearches, data, ids, requestFields } =
  useParallelChart<ConnectionField>(
    emit,
    ConnectionField.Id,
    props.fields,
    toRef(props, "query"),
    (fields, query) => connectionsApi.getConnectionsMatrix(fields, query)
  );
</script>

<template>
  <simple-parallel-chart
    :color="color"
    :data="data"
    :fields="fields"
    :ids="ids"
    label-prefix="connection."
    :request-fields="requestFields"
    @change:searches="changeSearches"
  >
    <template #title>
      <slot name="title" />
    </template>
  </simple-parallel-chart>
</template>
