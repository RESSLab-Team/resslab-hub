<script setup lang="ts">
import { ColumnField } from "@/backend";
import { columnsApi } from "@/plugins/axios";
import { defineProps, toRef, defineEmits } from "vue";
import { Color } from "vuetify/lib/util/colors";
import { Value } from "@/utils/common";
import { useSingleChart } from "@/utils/chart";
import SingleChart from "@/components/commons/charts/SingleChart.vue";

const props = defineProps<{
  color?: Color;
  field: ColumnField;
  query?: string;
}>();
const emit = defineEmits<{
  (e: "change:searches", key: string, value: Value): void;
}>();

const { counts } = useSingleChart<ColumnField>(
  props.field,
  toRef(props, "query"),
  (fields, query) => columnsApi.getColumnsCounts(fields, query)
);

function changeSearches(key: string, value: Value) {
  emit("change:searches", key, value);
}
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
