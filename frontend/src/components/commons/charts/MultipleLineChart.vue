<script setup lang="ts">
import { initOptions, updateOptions } from "@/components/commons/charts/utils";
import { primaryColor, secondaryColor } from "@/utils/vuetify";
import { EChartsOption, LineSeriesOption } from "echarts";
import { LineChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
} from "echarts/components";
import { use } from "echarts/core";
import { SVGRenderer } from "echarts/renderers";
import { computed, withDefaults, defineProps } from "vue";
import VChart from "vue-echarts";
import { Color } from "vuetify/lib/util/colors";
import { merge } from "lodash";

export interface Props {
  colors?: Color[];
  series?: LineSeriesOption[];
  aspectRatio?: number;
  maxWidth?: number;
  title: string;
  xAxisName: string;
  yAxisName: string;
}
const props = withDefaults(defineProps<Props>(), {
  colors: () => [primaryColor, secondaryColor],
  series: () => [],
  aspectRatio: 1,
  maxWidth: undefined,
  title: undefined,
  xAxisName: undefined,
  yAxisName: undefined,
});

use([
  SVGRenderer,
  LineChart,
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
]);

const option = computed<EChartsOption>(
  () =>
    ({
      title: {
        text: props.title,
        left: "center",
      },
      legend: {
        top: 30,
        show: props.series.length > 1,
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
        valueFormatter: (value: number) => value.toFixed(2),
      },
      series: props.series.map((serie) =>
        merge<LineSeriesOption, LineSeriesOption>(
          {
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
          },
          serie
        )
      ),
      color: props.colors.map((color) => color.base),
    } as EChartsOption)
);

const hasData = computed<boolean>(
  () => props.series.filter((serie) => serie.data?.length ?? 0 > 0).length > 0
);
</script>

<template>
  <v-responsive :aspect-ratio="aspectRatio" :max-width="maxWidth">
    <v-chart
      v-if="hasData"
      autoresize
      :init-options="initOptions"
      :option="option"
      :update-options="updateOptions"
    ></v-chart>
  </v-responsive>
</template>
