<template>
  <v-responsive aspect-ratio="1" :max-width="maxWidth">
    <v-chart v-if="hasData" autoresize :option="option"></v-chart>
  </v-responsive>
</template>

<script lang="ts">
import { primaryColor } from "@/utils/vuetify";
import { AxiosResponse } from "axios";
import { LineChart } from "echarts/charts";
import { GridComponent, TooltipComponent } from "echarts/components";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { EChartsOption } from "echarts/types/dist/shared";
import VChart from "vue-echarts";
import { Component, Prop, Vue, Watch } from "vue-property-decorator";
import { Color } from "vuetify/lib/util/colors";

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent]);

@Component({
  components: {
    VChart,
  },
})
export default class SimpleLineChart extends Vue {
  @Prop({ type: Object as () => Color, default: () => primaryColor })
  readonly color!: Color;
  @Prop({ type: Number, default: 300 })
  readonly maxWidth!: number;
  @Prop({ type: Promise })
  readonly promise: Promise<AxiosResponse<number[][]>> | undefined;
  @Prop({ type: String })
  readonly title: string | undefined;
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
      title: {
        text: this.title,
        left: "center",
      },
      grid: {
        left: 60,
        top: 32,
        right: 32,
        bottom: 60,
      },
      xAxis: {
        name: this.xAxisName,
        nameLocation: "middle",
        nameTextStyle: {
          fontWeight: "bold",
        },
        nameGap: 32,
      },
      yAxis: {
        name: this.yAxisName,
        nameLocation: "middle",
        nameTextStyle: {
          fontWeight: "bold",
        },
        nameGap: 46,
      },
      tooltip: {
        trigger: "axis",
      },
      series: [
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
          data: this.series,
        },
      ],
      color: this.color.base,
    };
  }

  get hasData(): boolean {
    return this.series.length > 0;
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
