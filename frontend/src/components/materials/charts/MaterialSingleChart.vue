<script setup lang="ts">
import { MaterialField } from "@/backend";
import { materialsApi } from "@/plugins/axios";
import SingleChart from "@/components/commons/charts/SingleChart.vue";
import { defineProps, toRef, defineEmits } from "vue";
import { Color } from "vuetify/lib/util/colors";
import { useSingleChart } from "@/utils/chart";
import { Value } from "@/utils/common";

const props = defineProps<{
  color?: Color;
  field: MaterialField;
  query?: string;
}>();
const emit = defineEmits<{
  (e: "change:searches", key: string, value: Value): void;
}>();

const { counts } = useSingleChart<MaterialField>(
  props.field,
  toRef(props, "query"),
  (fields, query) => materialsApi.getMaterialsCounts(fields, query)
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
    label-prefix="material."
    @change:searches="changeSearches"
  />
</template>
