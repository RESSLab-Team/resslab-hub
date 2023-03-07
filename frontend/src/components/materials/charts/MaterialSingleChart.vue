<script setup lang="ts">
import { MaterialField } from "@/backend";
import { materialsApi } from "@/plugins/axios";
import SingleChart from "@/components/commons/charts/SingleChart.vue";
import { defineProps, toRef, defineEmits } from "vue";
import {
  ChartEmits,
  singleChartProps,
  useSingleChart,
} from "@/composables/chart";

const props = defineProps(singleChartProps<MaterialField>());
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>();

const { counts, changeSearches } = useSingleChart<MaterialField>(
  emit,
  props.field,
  toRef(props, "query"),
  (fields, query) => materialsApi.getMaterialsCounts(fields, query)
);
</script>

<template>
  <single-chart
    :color="color"
    :counts="counts"
    :field="field"
    label-prefix="material."
    @change:searches="changeSearches"
  />
</template>
