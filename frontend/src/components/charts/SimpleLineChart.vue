<template>
  <v-chart :option="option"></v-chart>
</template>

<style scoped>
.echarts {
  min-height: 256px;
}
</style>

<script lang="ts">
import { Component, Prop, Vue, Watch } from "vue-property-decorator";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { LineChart } from "echarts/charts";
import { CanvasRenderer } from "echarts/renderers";
import { EChartsOption } from "echarts/types/dist/shared";
import colors, { Color } from "vuetify/lib/util/colors";
import { AxiosResponse } from "axios";
import { GridComponent, TooltipComponent } from "echarts/components";

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent]);

@Component({
  components: {
    VChart,
  },
})
export default class SimpleLineChart extends Vue {
  @Prop({ type: Object as () => Color, default: () => colors.blue })
  readonly color!: Color;
  @Prop({ type: Promise })
  readonly promise: Promise<AxiosResponse<number[][]>> | undefined;
  @Prop({ type: String })
  readonly xAxisName: string | undefined;
  @Prop({ type: String })
  readonly yAxisName: string | undefined;

  private series: number[][] = [];

  created(): void {
    this.onChanged();
  }

  get option(): EChartsOption {
    return {
      grid: {
        containLabel: true,
      },
      xAxis: {
        name: this.xAxisName,
        nameLocation: "middle",
        nameGap: 32,
      },
      yAxis: {
        name: this.yAxisName,
        nameLocation: "middle",
        nameGap: 50,
      },
      tooltip: {
        trigger: "axis",
      },
      series: [
        {
          type: "line",
          data: this.series,
        },
      ],
      color: this.color.base,
    };
  }

  @Watch("promise")
  onChanged(): void {
    if (this.promise) {
      this.promise
        .then((response) => response.data)
        .then((series) => {
          this.series = series;
        });
    }
  }
}
</script>
