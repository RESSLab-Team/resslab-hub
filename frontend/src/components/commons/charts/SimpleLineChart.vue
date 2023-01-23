<script setup lang="ts">
import MultipleLineChart from "@/components/commons/charts/MultipleLineChart.vue";
import { primaryColor } from "@/utils/vuetify";
import { Color } from "vuetify/lib/util/colors";
import { withDefaults, defineProps } from "vue";
import { Response } from "@/utils/detail";

export interface Props {
  color?: Color;
  maxWidth?: number;
  promise: Promise<Response>;
  title: string | undefined;
  xAxisName: string | undefined;
  yAxisName: string | undefined;
}
const props = withDefaults(defineProps<Props>(), {
  color: () => primaryColor,
  maxWidth: 300,
});
</script>

<template>
  <multiple-line-chart
    :colors="[props.color]"
    :max-width="props.maxWidth"
    :promises="[props.promise]"
    :title="props.title"
    :x-axis-name="props.xAxisName"
    :y-axis-name="props.yAxisName"
  ></multiple-line-chart>
</template>
