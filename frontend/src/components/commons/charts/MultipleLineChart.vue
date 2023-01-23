<script setup lang="ts">
import { initOptions, updateOptions } from "@/components/commons/charts/utils";
import { primaryColor, secondaryColor } from "@/utils/vuetify";
import { EChartsOption } from "echarts";
import { LineChart } from "echarts/charts";
import { GridComponent, TooltipComponent } from "echarts/components";
import { use } from "echarts/core";
import { SVGRenderer } from "echarts/renderers";
import {
  computed,
  onMounted,
  ref,
  watch,
  withDefaults,
  defineProps,
} from "vue";
import VChart from "vue-echarts";
import { Color } from "vuetify/lib/util/colors";
import { Response } from "@/utils/detail";

export interface Props {
  colors?: Color[];
  maxWidth?: number;
  promises?: Promise<Response>[];
  title: string | undefined;
  xAxisName: string | undefined;
  yAxisName: string | undefined;
}
const props = withDefaults(defineProps<Props>(), {
  colors: () => [primaryColor, secondaryColor],
  maxWidth: 300,
  promises: () => [],
});

use([SVGRenderer, LineChart, GridComponent, TooltipComponent]);

const seriesData = ref<number[][][]>([]);

onMounted(() => {
  onPromisesChanged(props.promises);
});

const option = computed<EChartsOption>(() => {
  return {
    title: {
      text: props.title,
      left: "center",
    },
    grid: {
      left: 96,
      top: 64,
      right: 32,
      bottom: 64,
    },
    xAxis: {
      name: props.xAxisName,
      nameLocation: "middle",
      nameTextStyle: {
        fontWeight: "bold",
      },
      nameGap: 32,
      axisLabel: {
        hideOverlap: true,
      },
    },
    yAxis: {
      name: props.yAxisName,
      nameLocation: "middle",
      nameTextStyle: {
        fontWeight: "bold",
      },
      nameGap: 70,
      axisLabel: {
        hideOverlap: true,
      },
    },
    tooltip: {
      trigger: "axis",
      confine: true,
    },
    series: seriesData.value
      .filter((data) => data !== undefined)
      .map((data) => ({
        type: "line",
        showSymbol: false,
        lineStyle: {
          width: 1,
        },
        emphasis: {
          lineStyle: {
            width: 1,
          },
        },
        data: data,
      })),
    color: props.colors.map((color) => color.base),
  };
});

const hasData = computed<boolean>(() => {
  return seriesData.value.filter((data) => data.length > 0).length > 0;
});

watch(() => props.promises, onPromisesChanged);

function onPromisesChanged(promises: Promise<Response>[]): void {
  Promise.all(promises).then(
    (promises) =>
      (seriesData.value = promises.map((response) =>
        Array.isArray(response) ? response : response.data
      ))
  );
}
</script>

<template>
  <v-responsive aspect-ratio="1.2" :max-width="maxWidth">
    <v-chart
      v-if="hasData"
      autoresize
      :init-options="initOptions"
      :option="option"
      :update-options="updateOptions"
    ></v-chart>
  </v-responsive>
</template>
