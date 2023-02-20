<script setup lang="ts">
import { updateOptions } from "@/components/commons/charts/utils";
import { EChartsGlOption } from "@/utils/echarts-gl";
import { SurfaceChart } from "echarts-gl/charts";
import { Grid3DComponent } from "echarts-gl/components";
import { TooltipComponent } from "echarts/components";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { merge, round } from "lodash";
import VChart from "vue-echarts";
import { withDefaults, defineProps, computed } from "vue";

use([CanvasRenderer, SurfaceChart, Grid3DComponent, TooltipComponent]);

const props = withDefaults(
  defineProps<{
    option: EChartsGlOption;
    aspectRatio?: number;
  }>(),
  {
    aspectRatio: 1,
  }
);

const axisLabelMaxDigits = 2;

const actualOption = computed<EChartsGlOption>(() => {
  const defaultOption: EChartsGlOption = {
    tooltip: {
      confine: true,
    },
    grid3D: {
      viewControl: {
        distance: 260,
      },
    },
    xAxis3D: {
      min: "dataMin",
      max: "dataMax",
      axisLabel: {
        formatter: (value) => `${round(value, axisLabelMaxDigits)}`,
      },
    },
    yAxis3D: {
      min: "dataMin",
      max: "dataMax",
      axisLabel: {
        formatter: (value) => `${round(value, axisLabelMaxDigits)}`,
      },
    },
    zAxis3D: {
      min: "dataMin",
      max: "dataMax",
      axisLabel: {
        formatter: (value) => `${round(value, axisLabelMaxDigits)}`,
      },
    },
  };
  return merge(defaultOption, props.option);
});
</script>

<template>
  <v-responsive :aspect-ratio="aspectRatio">
    <v-chart
      autoresize
      :option="actualOption"
      :update-options="updateOptions"
    />
  </v-responsive>
</template>
