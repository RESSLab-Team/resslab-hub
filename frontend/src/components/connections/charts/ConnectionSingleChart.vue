<script setup lang="ts">
import { ConnectionField } from "@/backend";
import { connectionsApi } from "@/plugins/axios";
import { publicPath, Value } from "@/utils/common";
import { CallbackDataParams } from "echarts/types/dist/shared";
import { defineProps, toRef, defineEmits, ref } from "vue";
import { Color } from "vuetify/lib/util/colors";
import { useSingleChart } from "@/utils/chart";
import SingleChart from "@/components/commons/charts/SingleChart.vue";

const props = defineProps<{
  color?: Color;
  field: ConnectionField;
  query?: string;
}>();
const emit = defineEmits<{
  (e: "change:searches", key: string, value: Value): void;
}>();

const { counts } = useSingleChart<ConnectionField>(
  props.field,
  toRef(props, "query"),
  (fields, query) => connectionsApi.getConnectionsCounts(fields, query)
);

const imageUrl = ref<string>();

function changeSearches(key: string, value: Value) {
  emit("change:searches", key, value);
}

function mouseover(params: CallbackDataParams): void {
  if (props.field === ConnectionField.ConnectionType) {
    const name: string = params.name.toLowerCase();
    imageUrl.value = publicPath + "img/connection-type/" + name + ".svg";
  }
}

function mouseout(): void {
  imageUrl.value = undefined;
}
</script>

<template>
  <single-chart
    :color="color"
    :counts="counts"
    :field="field"
    label-prefix="connection."
    @change:searches="changeSearches"
    @mouseover="mouseover"
    @mouseout="mouseout"
  >
    <template #default>
      <v-img
        v-if="imageUrl"
        aspect-ratio="3"
        contain
        :src="imageUrl"
        min-height="120"
      />
    </template>
  </single-chart>
</template>
