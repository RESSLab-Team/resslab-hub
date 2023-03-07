<script setup lang="ts">
import { BraceField } from "@/backend";
import { bracesApi } from "@/plugins/axios";
import { defineProps, toRef, defineEmits } from "vue";
import {
  useSingleChart,
  ChartEmits,
  singleChartProps,
} from "@/composables/chart";
import SingleChart from "@/components/commons/charts/SingleChart.vue";

const props = defineProps(singleChartProps<BraceField>());
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>();

const { counts, changeSearches } = useSingleChart<BraceField>(
  emit,
  props.field,
  toRef(props, "query"),
  (fields, query) => bracesApi.getBracesCounts(fields, query)
);
</script>

<template>
  <single-chart
    :color="color"
    :counts="counts"
    :field="field"
    label-prefix="brace."
    @change:searches="changeSearches"
  />
</template>
