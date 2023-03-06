<script setup lang="ts">
import { BraceField } from "@/backend";
import { bracesApi } from "@/plugins/axios";
import { defineProps, toRef, defineEmits } from "vue";
import { useSingleChart } from "@/utils/chart";
import { Color } from "vuetify/lib/util/colors";
import { Value } from "@/utils/common";
import SingleChart from "@/components/commons/charts/SingleChart.vue";

const props = defineProps<{
  color?: Color;
  field: BraceField;
  query?: string;
}>();
const emit = defineEmits<{
  (e: "change:searches", key: string, value: Value): void;
}>();

const { counts } = useSingleChart<BraceField>(
  props.field,
  toRef(props, "query"),
  (fields, query) => bracesApi.getBracesCounts(fields, query)
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
    label-prefix="brace."
    @change:searches="changeSearches"
  />
</template>
